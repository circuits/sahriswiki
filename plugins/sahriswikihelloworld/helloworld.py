from sahris.plugin import expose, BasePlugin

class HelloWorld(BasePlugin):

    @expose("+hello")
    def hello(self, *args, **kwargs):
        page = {"name": "HelloWorld",
                "text": "Hello World!"}

        data = {"page": page}

        return self.render("view.html", **data)
