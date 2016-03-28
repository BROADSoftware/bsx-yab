# bsx project

BSX if an infrastructure project aimed to automate cluster deployement for BigData application/

This both on bare metal and on virtualized (KVM) instrastructure. 

Application such as Hadoop, Kafka, Cassandra, etc... (All NoSQL world) share some specifics requirements:
- Use commodity hardware.
- Store large amount of data.
- Perform best on Direct Attached Storage (DAS).
- Handle data resiliency at application level.

BSX is designed to handle these requirements, especially by the management of a DAS based infrastructure.

It is made of several project:

- bsx-yab: A tool which take a yaml file describing a cluster and generate all scripts and ansible playbook to build it.
- bsx-stats: A tool to grab information on current infrastructure state, in order to plan new clusters.
- bsx-roles: A set of ansible roles, used to deploy a cluster  



