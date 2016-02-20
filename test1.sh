
if [ ! -f test/out1/dnsmasq ]
then
cat >test/out1/dnsmasq <<EOF

nameservers:
  - localhost   

dnsmasq_upstream_dns:
  - 5.196.10.92
  - 151.80.118.11

dnsmasq:
  upstream_dns: "{{ dnsmasq_upstream_dns }}"
  
  hosts:
  # Internet addresses
  - { ip: 185.103.142.145, fqdn:     hexatom-gw.bsa.broadsoftware.com,           aliases: [ hexatom-gw ] }
  - { ip: 185.103.142.146, fqdn:     hexatom-reserved1.bsa.broadsoftware.com,    aliases: [ hexatom-reserved1 ] }
  - { ip: 185.103.142.147, fqdn:     hexatom-reserved2.bsa.broadsoftware.com,    aliases: [ hexatom-reserved2 ] }
  
  - { ip: 185.103.142.148, fqdn:     unused148.bsa.broadsoftware.com,            aliases: [ unused148 ] }
  - { ip: 185.103.142.149, fqdn:     unused149.bsa.broadsoftware.com,            aliases: [ unused149 ] }
  - { ip: 185.103.142.150, fqdn:     unused150.bsa.broadsoftware.com,            aliases: [ unused150 ] }
  - { ip: 185.103.142.151, fqdn:     gate1i.bsa.broadsoftware.com,               aliases: [ gate1i ] }
  - { ip: 185.103.142.152, fqdn:     gate2i.bsa.broadsoftware.com,               aliases: [ gate2i ] }
  - { ip: 185.103.142.153, fqdn:     unused153.bsa.broadsoftware.com,            aliases: [ unused153 ] }
  - { ip: 185.103.142.154, fqdn:     unused154.bsa.broadsoftware.com,            aliases: [ unused154 ] }
  - { ip: 185.103.142.155, fqdn:     bsa5i.bsa.broadsoftware.com,                aliases: [ bsa5i ] }
  - { ip: 185.103.142.156, fqdn:     bsa6i.bsa.broadsoftware.com,                aliases: [ bsa6i ] }
  - { ip: 185.103.142.157, fqdn:     unused157.bsa.broadsoftware.com,            aliases: [ unused157 ] }
  - { ip: 185.103.142.158, fqdn:     unused158.bsa.broadsoftware.com,            aliases: [ unused158 ] }
  - { ip: 185.103.142.159, fqdn:     unused159.bsa.broadsoftware.com,            aliases: [ unused159 ] }

EOF
fi
	

python yab.py --src test/test1.yml --build test/out1/build --cmd test/out1/cmd --ssh test/out1/ssh --dnsmasq test/out1/dnsmasq
