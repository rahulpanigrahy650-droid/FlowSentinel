# VPN Troubleshooting Runbook

## Symptoms
VPN client will not connect, disconnects repeatedly, or connects but internal sites do not load. Applies to GlobalProtect, Cisco AnyConnect and OpenVPN clients.

## Frequent disconnects
1. Confirm the user's home network is stable: run a continuous ping to 8.8.8.8 for two minutes and look for packet loss.
2. Switch from Wi-Fi 2.4 GHz to 5 GHz or to a wired connection; weak Wi-Fi is the most common cause of VPN drops every few minutes.
3. Disable power saving on the Wi-Fi adapter (Device Manager > Network adapter > Power Management).
4. Update the VPN client to the current approved version from the software portal.
5. In the client settings switch the protocol from IPsec to SSL (TCP 443) if the ISP or router blocks UDP 500/4500.
6. If drops continue, collect the client log bundle and escalate to Network Operations.

## Connects but internal sites do not load
1. Check the assigned VPN IP address and DNS servers (`ipconfig /all`).
2. Flush the DNS cache with `ipconfig /flushdns` and retry.
3. Confirm the user is in the correct VPN group; missing group membership gives a tunnel with no routes.

## Escalate if
More than 10 users are affected at once or the VPN gateway health check is failing.
