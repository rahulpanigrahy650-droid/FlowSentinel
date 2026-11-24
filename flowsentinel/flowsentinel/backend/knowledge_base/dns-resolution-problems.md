# DNS Resolution Problems

## Symptoms
Hostnames resolve slowly or not at all, websites load by IP but not by name, only one office or subnet is affected.

## Steps
1. Test resolution against each DNS server: `nslookup host <dns-server-ip>` and compare response times.
2. Identify which DNS servers the clients receive from DHCP and confirm they are the intended internal resolvers.
3. If one resolver is slow or down, remove it from the DHCP scope temporarily or restart the DNS service on it.
4. Check forwarders and conditional forwarders for the office; a failing upstream forwarder causes 5 to 10 second delays.
5. Flush client caches with `ipconfig /flushdns` and the server cache with `Clear-DnsServerCache`.
6. Check the WAN link of the affected site for latency and packet loss.

## Escalate if
Multiple sites fail to resolve internal names: escalate to Network Operations.
