from mininet.node import Host, Node
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.link import Link, TCLink


def main():
    # network setup
    net = mininet.Mininet(link=TCLink)

    t = net.addHost('t')
    p1 = net.addHost('p1')
    p2 = net.addHost('p2')
    p3 = net.addHost('p3')
    s = net.addSwitch('s')

    net.addLink(t, s)
    net.addLink(p1, s)
    net.addLink(p2, s)
    net.addLink(p3, s)

    net.build()

    # BitTorrent setup
    # tracker
    t.cmd(f'python src/bittorrent/tracker.py -N tracker -D sandbox/tracker/ -H {t.IP()} -P 7889')

    # peers
    p1.cmd(f'python src/bittorrent/peer.py -N p1 -D sandbox/peer/1/ -H {p1.IP()} -P 7890')
    p2.cmd(f'python src/bittorrent/peer.py -N p2 -D sandbox/peer/2/ -H {p2.IP()} -P 7890')
    p3.cmd(f'python src/bittorrent/peer.py -N p3 -D sandbox/peer/3/ -H {p3.IP()} -P 7890')

    # BitTorrent download
    p1.cmd(f'd sandbox/peer/1/.torrents/text.torrent')


if __name__ == "__main__":
    main()