
import sys
import os
import errno
import yaml
from easydict import EasyDict as edict
import socket
import jinja2
import hashlib
import ipaddress
import fileinput
import re
import traceback
import pprint

dumpModel=True

def usage():
    print """Usage: yab.py <sourceFile> <buildOutputFolder> [<cmdOutputFolder>] 

Will build a set of build files in <buildOutputFolder>

This from <sourceFile>, which is a yaml file describing the infrastructure to build

Optionally, add cluster start/stop/... scripts in cmdOutputFolder

"""

infraConfigMandatoryAttributes = ["networks", "deviceFromIndex", "hosts", "infra_domain", "cobbler_host"]
infraConfigAllowedAttributes = set(infraConfigMandatoryAttributes).union(set([]))

envConfigMandatoryAttributes = ["kvm_script_path", "keys_location", "roles_path"]
envConfigAllowedAttributes = set(envConfigMandatoryAttributes).union(set([]))

networkMandatoryAttributes = ["name", "base", "bridge", "netmask", "broadcast", "gateway", "dns"] 
networkAllowedAttributes = set(networkMandatoryAttributes).union(set([]))

clusterMandatoryAttributes = ["id", "domain", "patterns", "nodes", "default_network"]
clusterAllowedAttributes = set(clusterMandatoryAttributes).union(set([]))
 
nodeMandatoryAttributes = ["name", "pattern", "host"] 
nodeAllowedAttributes = set(nodeMandatoryAttributes).union(set(["blueprint_host_group", "hostname", "base_volume_index", "volume_indexes", "root_volume_index", "ip", "vmname", "network"]))

patternMandatoryAttributes = ["name", "root_size", "memory", "vcpu"] 
patternAllowedAttributes = set(patternMandatoryAttributes).union(set(["data_disks"]))

def ERROR(err):
    if type(err) is str:
        message = err
    else:
        message = err.__class__.__name__ + ": " + str(err)
    print "* * * * ERROR: " + str(message)
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
        
def findYabConfig(fileName, initial, location, cpt):
    x = os.path.join(location , fileName)
    if os.path.isfile(x):
        # Found !
        print "Use '{0}' as config file".format(x)
        return edict(yaml.load(open(x)))
    else:
        if location == "" or location == "/" :
            ERROR("Unable to locate a {0} file in '{1}' and upward".format(fileName, initial))
        else:
            if cpt < 20:
                return findYabConfig(fileName, initial, os.path.dirname(location), cpt + 1)
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

def adjustInfraConfig(config):
    checkAttributes(config, infraConfigMandatoryAttributes, infraConfigAllowedAttributes)
    for network in config.networks:
        checkAttributes(network, networkMandatoryAttributes, networkAllowedAttributes)
        network.cidr = ipaddress.IPv4Network("" + network.base + "/" + network.netmask, strict=True) 
        if ipaddress.ip_address(network.gateway) not in network.cidr:
            ERROR("Gateway '{0}' not in network {1}".format(network.gateway, network))
    config.networkByName = dict((network.name, network) for network in config.networks)
    
def adjustEnvConfig(config):
    checkAttributes(config, envConfigMandatoryAttributes, envConfigAllowedAttributes)

def buildVolumeList(config, node):
    # -------------------------------- Handle root disk
    if 'root_volume_index' in node:
        idx = node.root_volume_index
    else:
        idx = 0
    nbrRootVolumes = len(config.hosts[node.host].root_volumes)
    node.root_volume = config.hosts[node.host].root_volumes[idx % nbrRootVolumes]
    # ----------------------------- Handle Data disks
    if "data_disks" in node.features and len(node.features.data_disks) > 0:
        nbrDataVolume = len(config.hosts[node.host].data_volumes)
        if "base_volume_index" in node:
            for i in range(len(node.features.data_disks)):
                node.features.data_disks[i].volume = config.hosts[node.host].data_volumes[(i + node.base_volume_index) % nbrDataVolume]
        elif "volume_indexes" in node:
            if len(node.volume_indexes) != nbrDataVolume:
                ERROR("Node {0}: volume_indexes size ({1} != host.data_volumes size ({2})".format(node.name, len(node.volume_indexes),nbrDataVolume))
            for i in range(len(node.features.data_disks)):
                node.features.data_disks[i].volume = config.hosts[node.host].data_volumes[node.volume_indexes[i]]
        else:
            ERROR("Node {0}: Either 'base_volume_index' or 'volume_indexes' must be defined!".format(node.name))

        
def adjustCluster(cluster, config):
    checkAttributes(cluster, clusterMandatoryAttributes, clusterAllowedAttributes)
    for pattern in cluster.patterns:
        checkAttributes(pattern, patternMandatoryAttributes, patternAllowedAttributes)
        if "data_disks" in pattern:
            for i in range(0, len(pattern.data_disks)):
                pattern.data_disks[i].device = config.deviceFromIndex[i]
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
        buildVolumeList(config, node)
            
startPattern = re.compile(r"^#\s+YAB_INCLUDE\[(.+)\]_BEGIN\s.*$")        
endPattern = re.compile(r"^#\s+YAB_INCLUDE\[(.+)\]_END\s.*$")        

class TmplInjectionError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)     



def regenerate(jinja2env, model, templateName, targetFolder, outputFileName):
    outputPath = os.path.join(targetFolder, outputFileName) 
    print("Generate a brand-new {0}".format(outputPath))
    tmpl = jinja2env.get_template(templateName + ".j2")
    f = open(outputPath, 'w')
    x = tmpl.render(m=model)
    f.write(x)
    f.close()



def generate(jinja2env, model, templateName, targetFolder, outputFileName):
    outputPath = os.path.join(targetFolder, outputFileName) 
    # --------------------------------------------------------- Create initial file if not existing
    if not os.path.isfile(outputPath):
        print("Generate a brand-new {0}".format(outputPath))
        tmpl = jinja2env.get_template(templateName + ".j2")
        f = open(outputPath, 'w')
        x = tmpl.render(m=model)
        f.write(x)
        f.close()
    else:
        print("Adjust {0}".format(outputPath))
        
    # -------------------------------------------------------- And now rewrite the file with sub-template injection
    group = None
    try:
        for line in fileinput.FileInput(outputPath, inplace=1, backup=".bak"):
            if group != None:
                m = endPattern.match(line) 
                if m:
                    if m.group(1) != group:
                        raise TmplInjectionError("YAB_{0}_BEGIN.... YAB_{1}_END tag mismatch!".format(group, m.group(1)))
                    else:
                        sys.stdout.write(line)
                        group = None
            else:
                sys.stdout.write(line)
                m = startPattern.match(line)
                if m:
                    group = m.group(1)  
                    tmpl = jinja2env.get_template(group + ".j2")
                    sys.stdout.write(tmpl.render(m=model))
        if group:
            raise TmplInjectionError("Unenclosed last YAB_{0}_BEGIN tag".format(group))
    except Exception:
        # ---------------- Will rollback by moving backup file in place.
        os.rename(outputPath + ".bak", outputPath)
        traceback.print_exc()
        #ERROR(e)
    # And remove the backup file
    try:
        os.remove(outputPath + ".bak")
    except:
        pass
    
        
import argparse        
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', required=True)
    parser.add_argument('--build')
    parser.add_argument('--cmd')
    parser.add_argument('--ssh')
    param = parser.parse_args()

    #print(param)    
    
    mydir =  os.path.dirname(os.path.realpath(__file__)) 
    sourceFile = param.src
    targetBuildFolder = param.build
    targetCmdFolder= param.cmd
    targetSshFolder= param.ssh

    if not os.path.isfile(sourceFile):
        print "{0} is not a readable file!".format(sourceFile)
        sys.exit(1)
        
    sourceFileDir = os.path.dirname(os.path.realpath(sourceFile))
    infraConfig = findYabConfig('yab-infra.yml', sourceFileDir, sourceFileDir, 0)
    adjustInfraConfig(infraConfig)
    envConfig = findYabConfig('yab-env.yml', sourceFileDir, sourceFileDir, 0)
    adjustEnvConfig(envConfig)
        
    cluster = edict(yaml.load(open(sourceFile)))
    adjustCluster(cluster, infraConfig)
    
    if targetBuildFolder:
        targetHostVarsFolder = os.path.join(targetBuildFolder ,'host_vars') 
        targetGroupVarsFolder = os.path.join(targetBuildFolder ,'group_vars') 
        ensureFolder(targetBuildFolder)
        ensureFolder(targetHostVarsFolder)
        ensureFolder(targetGroupVarsFolder)
    if targetCmdFolder:
        ensureFolder(targetCmdFolder)
    if targetSshFolder:
        ensureFolder(targetSshFolder)

    if dumpModel:
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(infraConfig)
        pp.pprint(envConfig)
        pp.pprint(cluster)

    model = edict({})
    model.cluster = cluster
    model.infra = infraConfig
    model.env = envConfig
    jinja2env = jinja2.Environment(loader = jinja2.FileSystemLoader(os.path.join(mydir, 'templates')), undefined = jinja2.StrictUndefined, trim_blocks = True)
    if targetBuildFolder:
        generate(jinja2env, model, "build.sh", targetBuildFolder, "build.sh")
        generate(jinja2env, model, "inventory", targetBuildFolder, "inventory")
        generate(jinja2env, model, "ansible.cfg", targetBuildFolder, "ansible.cfg")
        generate(jinja2env, model, "group_vars-all", targetGroupVarsFolder, "all")
        for node in cluster.nodes:
            model.node = node
            generate(jinja2env, model, "host_vars", targetHostVarsFolder, node.name)
    if targetCmdFolder:
        regenerate(jinja2env, model, "startCluster.sh", targetCmdFolder, "startCluster.sh")
        regenerate(jinja2env, model, "stopCluster.sh", targetCmdFolder, "stopCluster.sh")
        regenerate(jinja2env, model, "statusCluster.sh", targetCmdFolder, "statusCluster.sh")
        regenerate(jinja2env, model, "deleteCluster.sh", targetCmdFolder, "deleteCluster.sh")
    if targetSshFolder:
        for node in cluster.nodes:
            model.node = node
            regenerate(jinja2env, model, "ssh", targetSshFolder, node.name)
        

if __name__ == "__main__":
    main()
