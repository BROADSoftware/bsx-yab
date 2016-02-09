
import sys
import os
import errno
import yaml
import pprint
from easydict import EasyDict as edict
import socket
import jinja2
import hashlib
import ipaddress

def usage():
    print """Usage: yab.py <sourceFile> <targetFolder> [<configFile>]
Will build or patch:
	<targetFolder>/build/build1.sh		# The script who create the VMs
	<targetFolder>/build/build2.sh		# The script who create the secondaries disks

This from <sourceFile>, which is a yaml file describing the infrastructure to build

<configFile> is also a yaml file containing system wide definitions, such as network definition, repositories location, etc...
    If not provided, it will be looked up as
        <sourceFileDir>/yab-config.yml
        <sourceFileDir>/../yab-config.yml
        <sourceFileDir>/../../yab-config.yml
        And so on recursivly up to /
"""

configMandatoryAttributes = ["networks", "create_vm_script", "keys_location"]
configAllowedAttributes = set(configMandatoryAttributes).union(set([]))

networkMandatoryAttributes = ["name", "base", "bridge", "netmask", "gateway", "dns"] 
networkAllowedAttributes = set(networkMandatoryAttributes).union(set([]))

clusterMandatoryAttributes = ["id", "domain", "patterns", "nodes", "default_network"]
clusterAllowedAttributes = set(clusterMandatoryAttributes).union(set([]))
 
nodeMandatoryAttributes = ["name", "pattern", "host"] 
nodeAllowedAttributes = set(nodeMandatoryAttributes).union(set(["blueprint_host_group", "hostname", "base_volume_index", "ip", "vmname", "network"]))

patternMandatoryAttributes = ["name", "root_size", "memory", "vcpu"] 
patternAllowedAttributes = set(patternMandatoryAttributes).union(set(["data_disks"]))

def ERROR(message):
    print "* * * * ERROR: " + message
    exit(1)

def ensureFolder(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
        else:
            pass
        
def checkAttributes(obj, mandatoryAttributes, allowedAttributes):
    for n in mandatoryAttributes:
        if not n in obj:
            ERROR("Missing attribute '{0}' in object: {1}".format(n, obj))        
    for attr in obj.keys():
        if attr not in allowedAttributes:
            ERROR("Invalid attribute '{0}' in object: {1}".format(attr, obj)) 
       
def resolveDns(fqdn):
    try: 
        return socket.gethostbyname(fqdn)
    except socket.gaierror:
        return None
        
def findYabConfig(initial, location, cpt):
    x = os.path.join(location ,'yab-config.yml')
    if os.path.isfile(x):
        # Found !
        print "Use '{0}' as config file".format(x)
        return edict(yaml.load(open(x)))
    else:
        if location == "" or location == "/" :
            ERROR("Unable to locate a yab-config.yml file in '{0}' and upward".format(initial))
        else:
            if cpt < 20:
                findYabConfig(initial, os.path.dirname(location), cpt + 1)
            else:
                raise Exception("Too many lookup")
            

                
       
def adjustIP(node, domain):
    fqdn = node.hostname + "." + domain
    addr = resolveDns(fqdn)
    if addr == None:
        if not "ip" in node:
            ERROR("Unable to lookup an IP for node '{0}'. Unresolved and not defined!".format(node.name))
    else:
        if "ip" in node:
            if node.ip != addr:
                ERROR("IP mismatch for node '{0}'. Resolved to '{1}' but defined to '{2}'".format(node.name, addr, node.ip))
        else:
            node.ip = addr


""" As we may regenerate some VM several times, during testing. it is important to provide the same
MAC address for a given IP, otherwise others nodes will detect an IP address conflict.
"""
def generateMac(ip):
    s = hashlib.md5(ip).hexdigest()
    m = "52:54:00:{0}:{1}:{2}".format(s[0:2], s[2:4], s[4:6])
    return m

def adjustConfig(config):
    checkAttributes(config, configMandatoryAttributes, configAllowedAttributes)
    for network in config.networks:
        checkAttributes(network, networkMandatoryAttributes, networkAllowedAttributes)
        network.cidr = ipaddress.IPv4Network("" + network.base + "/" + network.netmask, strict=True) 
        if ipaddress.ip_address(network.gateway) not in network.cidr:
            ERROR("Gateway '{0}' not in network {1}".format(network.gateway, network))
    config.networkByName = dict((network.name, network) for network in config.networks)
    
        
def adjustCluster(cluster, config):
    checkAttributes(cluster, clusterMandatoryAttributes, clusterAllowedAttributes)
    for pattern in cluster.patterns:
        checkAttributes(pattern, patternMandatoryAttributes, patternAllowedAttributes)
    if cluster.default_network not in config.networkByName:
        ERROR("Invalid cluster.default_network: '{0}'".format(cluster.default_network))  
    cluster.defaultNetwork = config.networkByName[cluster.default_network]
    cluster.groups = dict((pattern.name, []) for pattern in cluster.patterns)
    patternByName = dict((pattern.name, pattern) for pattern in cluster.patterns)
    nodeByIp = edict({})
    for node in cluster.nodes:
        checkAttributes(node, nodeMandatoryAttributes, nodeAllowedAttributes)
        if node.pattern not in patternByName:
            ERROR("Invalid pattern '{0}' for node {1}".format(node.pattern, node))
        node.features = patternByName[node.pattern]
        node.features.name = None   # Redundant with pattern name.
        cluster.groups[node.pattern].append(node['name'])
        if "vmname" not in node:
            node.vmname = cluster.id + "_" + node.name
        if "hostname" not in node:
            node.hostname = node.name        
        adjustIP(node, cluster.domain)
        if node.ip not in nodeByIp:
            nodeByIp[node.ip] = node
        else:
            ERROR("Same IP used for both node '{0}' and '{1}'".format(nodeByIp[node.ip].name, node.name))
        if 'mac' not in node:
            node.mac = generateMac(node.ip)
        if 'network' in node:
            if node.network not in config.networkByName:
                ERROR("Invalid network '{0}' in node {1}".format(node.network, node))
            else:
                node.network = config.networkByName[node.network]
            pass
        else:
            node.network = cluster.defaultNetwork
        if ipaddress.ip_address(node.ip) not in node.network.cidr:
            ERROR("IP '{0}' not in network '{1}' for node {2}".format(node.ip, node.network.name, node))
        if 'root_volume_index' not in node:
            node.root_volume_index = 0
        node.root_volume = "/vol%02d" % node.root_volume_index
            
        
        
def generate(jinja2env, model, templateName, targetFolder, outputFileName):
    outputPath = os.path.join(targetFolder, outputFileName) 
    tmpl = jinja2env.get_template(templateName + ".j2")
    f = open(outputPath, 'w')
    x = tmpl.render(m=model)
    f.write(x)
    f.close()    
        
        
        
def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        usage()
        sys.exit(1)
    
    mydir =  os.path.dirname(os.path.realpath(__file__)) 
    sourceFile = sys.argv[1]
    targetFolder = sys.argv[2]
    sourceFileDir = os.path.dirname(os.path.realpath(sourceFile))
    config = findYabConfig(sourceFileDir, sourceFileDir, 0)
    adjustConfig(config)
        
    if not os.path.isfile(sourceFile):
        print "{0} is not a readable file!".format(sourceFile)
        sys.exit(1)
        
    cluster = edict(yaml.load(open(sourceFile)))
    adjustCluster(cluster, config)
    
    targetBuildFolder = os.path.join(targetFolder ,'build') 
    ensureFolder(targetFolder)
    ensureFolder(targetBuildFolder)

    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(config)
    pp.pprint(cluster)

    model = edict({})
    model.cluster = cluster
    model.config = config
    
    jinja2env = jinja2.Environment(loader = jinja2.FileSystemLoader(os.path.join(mydir, 'templates')), undefined = jinja2.StrictUndefined, trim_blocks = True)
    generate(jinja2env, model, "build1.sh", targetBuildFolder, "build1.sh")

if __name__ == "__main__":
    main()
