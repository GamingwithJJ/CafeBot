class Verse:
    text = ""
    reference = ""
    version = ""

    def __init__(self, text: str, reference: str, version: str):
        self.text = text
        self.reference = reference
        self.version = version

    def get_text(self):
        return self.text

    def get_reference(self):
        return self.reference

    def get_version(self):
        return self.version

    def to_dict(self):
        return {
            "text": self.text,
            "reference": self.reference,
            "version": self.version
        }