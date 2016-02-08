
import sys
import os
import errno
import yaml
import pprint
from easydict import EasyDict as edict
import socket
import jinja2

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


clusterMandatoryAttributes = ["id", "domain", "patterns", "nodes"] 
nodeMandatoryAttributes = ["name", "pattern", "host"] 
patternMandatoryAttributes = ["name", "root_size", "memory", "vcpu"] 

def ensureFolder(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
        else:
            pass
        
def checkMandatoryAttribute(obj, attributeNames):
    for n in attributeNames:
        if not n in obj:
            raise Exception("Missing attribute '{0}' in object: {1}".format(n, obj))        
       
def resolveDns(fqdn):
    try: 
        return socket.gethostbyname(fqdn)
    except socket.gaierror:
        return None
        
def findYabConfig(initial, location, cpt):
    x = os.path.join(location ,'yab-config.yml')
    print "lookup for '{0}'".format(x)
    if os.path.isfile(x):
        # Found !
        return edict(yaml.load(open(x)))
    else:
        if location == "" or location == "/" :
            raise Exception("Unable to locate a yab-config.yml file in '{0}' and upward".format(initial))
        else:
            if cpt < 10:
                findYabConfig(initial, os.path.dirname(location), cpt + 1)
            else:
                raise Exception("Too many lookup")
            

                
       
def checkIp(node, domain):
    fqdn = node.hostname + "." + domain
    addr = resolveDns(fqdn)
    if addr == None:
        if not "ip" in node:
            raise Exception("Unable to lookup an IP for node '{0}'. Unresolved and not defined!".format(node.name))
    else:
        if "ip" in node:
            if node.ip != addr:
                raise Exception("IP mismatch for node '{0}'. Resolved to '{1}' but defined to '{2}'".format(node.name, addr, node.ip))
        else:
            node.ip = addr
        
def adjust(cluster):
    checkMandatoryAttribute(cluster, clusterMandatoryAttributes)
    for pattern in cluster.patterns:
        checkMandatoryAttribute(pattern, patternMandatoryAttributes)
    cluster.groups = dict((pattern.name, []) for pattern in cluster.patterns)
    patternByName = dict((pattern.name, pattern) for pattern in cluster.patterns)
    nodeByIp = edict({})
    for node in cluster.nodes:
        checkMandatoryAttribute(node, nodeMandatoryAttributes)
        node.features = patternByName[node.pattern]
        node.features.name = None   # Redundant with pattern name.
        cluster.groups[node.pattern].append(node['name'])
        if "vmname" not in node:
            node.vmname = cluster.id + "_" + node.name
        if "hostname" not in node:
            node.hostname = node.name        
        checkIp(node, cluster.domain)
        if node.ip not in nodeByIp:
            nodeByIp[node.ip] = node
        else:
            raise Exception("Same IP used for both node '{0}' and '{1}'".format(nodeByIp[node.ip].name, node.name))
        
def generate(jinja2env, model, templateName, outputFileName):
    tmpl = jinja2env.get_template(templateName + ".j2")
    f = open(outputFileName, 'w')
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
        
    if not os.path.isfile(sourceFile):
        print "{0} is not a readable file!".format(sourceFile)
        sys.exit(1)
        
    cluster = edict(yaml.load(open(sourceFile)))
    adjust(cluster)
    
    targetBuildFolder = os.path.join(targetFolder ,'build') 
    ensureFolder(targetFolder)
    ensureFolder(targetBuildFolder)

    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(cluster)

    model = edict({})
    model.cluster = cluster
    
    jinja2env = jinja2.Environment(loader = jinja2.FileSystemLoader(os.path.join(mydir, 'templates')), undefined = jinja2.StrictUndefined, trim_blocks = True)
    generate(jinja2env, model, "build1.sh", "build1.sh")

if __name__ == "__main__":
    main()
