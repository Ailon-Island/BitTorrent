# torrent file parser: convert a file into a .torrent metafile, and vice versa


class Torrent:
    def __init__(self, piece_len=4096):
        self.file = {
            'announce': None,
            'port': None,
            'comment': "",
            'info': {
                'name': None,
                'files': [],
            }
        }

        self.piece_len = piece_len

    @property
    def announce(self):
        return self.file['announce']

    @announce.setter
    def announce(self, announce):
        self.file['announce'] = announce

    @property
    def port(self):
        return self.file['port']

    @port.setter
    def port(self, port):
        self.file['port'] = port

    @property
    def comment(self):
        return self.file['comment']

    @comment.setter
    def comment(self, comment):
        self.file['comment'] = comment

    @property
    def info(self):
        return self.file['info']

    @info.setter
    def info(self, info):
        self.file['info'] = info

    def add_file(self, file, file_name, file_dir