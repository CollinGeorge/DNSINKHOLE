import socket
import logging
from dnslib import DNSRecord, DNSHeader, DNSQuestion, DNSRR, QTYPE, CLASS
from dnslib.server import DNSServer, DNSHandler, BaseResolver

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the IP address and port to listen on
listen_ip = "0.0.0.0"
listen_port = 53

# Define the domain names to sinkhole
blocked_domains = ["example.com", "test.com", "blockeddomain.com"]

# Custom DNS resolver
class SinkholeResolver(BaseResolver):
    def resolve(self, request, handler):
        # Extract the domain name from the DNS query
        domain = request.q.qname

        # Check if the domain is in the blocked domains list
        if str(domain) in blocked_domains:
            # If the domain is blocked, construct a DNS response with a sinkhole IP
            reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)
            
            if request.q.qtype in [QTYPE.A, QTYPE.AAAA]:
                # Block A and AAAA records by responding with a sinkhole IP
                sinkhole_ip = "127.0.0.1"  # Sinkhole IP
                reply.add_answer(DNSRR(
                    rrname=domain,
                    rtype=request.q.qtype,
                    rclass=CLASS.IN,
                    ttl=60,
                    rdata=socket.inet_aton(sinkhole_ip)
                ))
                logger.info(f"Blocked DNS query for {domain} (Type: {QTYPE[request.q.qtype]})")

            elif request.q.qtype == QTYPE.CNAME:
                # Block CNAME records by responding with a sinkhole domain
                sinkhole_cname = "blockeddomain.local"  # Sinkhole CNAME
                reply.add_answer(DNSRR(
                    rrname=domain,
                    rtype=request.q.qtype,
                    rclass=CLASS.IN,
                    ttl=60,
                    rdata=sinkhole_cname
                ))
                logger.info(f"Blocked DNS query for {domain} (Type: {QTYPE[request.q.qtype]})")

            else:
                # Pass through other record types without blocking
                reply = super().resolve(request, handler)
        else:
            # If the domain is not blocked, pass through the DNS query to the upstream DNS server
            reply = super().resolve(request, handler)

        return reply

# Start the DNS server with the sinkhole resolver
resolver = SinkholeResolver()
server = DNSServer(resolver, address=listen_ip, port=listen_port)
server.start_thread()

logger.info(f"DNS sinkhole is active. Listening on {listen_ip}:{listen_port}...")

# Wait for the server to exit (e.g., by pressing Ctrl+C)
try:
    server.join()
except KeyboardInterrupt:
    pass

# Stop the server
server.stop()