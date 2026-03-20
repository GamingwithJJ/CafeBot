class Quote:
    text = ""
    author = "" # Contains strings of their names
    tags = []

    def __init__(self, text: str, author: str):
        self.text = text
        self.author = author

    def get_text(self):
        return self.text

    def get_author(self):
        return self.author

    def get_tags(self):
        return self.tags

    def set_text(self, text: str):
        self.text = text

    def set_author(self, author: list):
        self.author = author

    def set_tags(self, tags: list):
        self.tags = tags

    def add_tag(self, tag: str):
        self.tags.append(tag)

    def __str__(self):
        return f"{self.text} - {self.author}"

    def to_dict(self):
        return {
            "text": self.text,
            "author": self.author,
            "tags": self.tags
        }