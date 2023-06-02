from mininet.node import Host, Node
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.link import Link, TCLink
from mininet.node import OVSKernelSwitch


ips = {
    't': '10.0.0.1/24',
    'p1': '10.0.0.2/24',
    'p2': '10.0.0.3/24',
    'p3': '10.0.0.4/24',
}


def main():
    # network setup
    net = Mininet(link=TCLink)

    t = net.addHost('t', ip=ips['t'])
    p1 = net.addHost('p1', ip=ips['p1'])
    p2 = net.addHost('p2', ip=ips['p2'])
    p3 = net.addHost('p3', ip=ips['p3'])
    s1 = net.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')

    net.addLink(t, s1)
    net.addLink(p1, s1)
    net.addLink(p2, s1)
    net.addLink(p3, s1)

    net.build()

    net.get('s1').start([])

    # s1.cmd('sysctl net.ipv4.ip_forward=1')

    # # BitTorrent setup
    # # tracker
    # t.cmd(f'python src/bittorrent/tracker.py -N tracker -D sandbox/tracker/ -H {t.IP()} -P 7889')

    # # peers
    # p1.cmd(f'python src/bittorrent/peer.py -N p1 -D sandbox/peer/1/ -H {p1.IP()} -P 7890')
    # p2.cmd(f'python src/bittorrent/peer.py -N p2 -D sandbox/peer/2/ -H {p2.IP()} -P 7890')
    # p3.cmd(f'python src/bittorrent/peer.py -N p3 -D sandbox/peer/3/ -H {p3.IP()} -P 7890')

    
    # python src/bittorrent/tracker.py -N tracker -D sandbox/tracker/ -H 10.0.0.1 -P 7889

    # python src/bittorrent/peer.py -N p1 -D sandbox/peer/1/ -H 10.0.0.2 -P 7890
    # python src/bittorrent/peer.py -N p2 -D sandbox/peer/2/ -H 10.0.0.3 -P 7890
    # python src/bittorrent/peer.py -N p3 -D sandbox/peer/3/ -H 10.0.0.4 -P 7890

    
    # python src/bittorrent/tracker.py -N tracker -D sandbox/tracker/ -H 127.0.0.1 -P 17889

    # python src/bittorrent/peer.py -N p1 -D sandbox/peer/1/ -H 127.0.0.1 -P 17991
    # python src/bittorrent/peer.py -N p2 -D sandbox/peer/2/ -H 127.0.0.1 -P 17992
    # python src/bittorrent/peer.py -N p3 -D sandbox/peer/3/ -H 127.0.0.1 -P 17993

    # BitTorrent download
    p1.cmd(f'd sandbox/peer/1/.torrents/text.torrent')

    CLI(net)

    net.stop()
    

if __name__ == "__main__":
    main()