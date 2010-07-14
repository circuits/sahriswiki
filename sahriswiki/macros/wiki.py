"""Wiki macros"""

import re
import time

from genshi.builder import tag
from genshi import Markup

def set_title(macro, environ, context, *args, **kwargs):
    """Set the title of the page
    
    **Arguments:**
    * title (//the title//)
    * display=False (//True to render the title//)

    **Example(s):**
    {{{
    <<set-title "My Title">>
    }}}

    {{{
    <<set-title "My Title", display=True>>
    }}}
    """

    if args and args[0]:
        title = args[0]
        context["title"] = title
        if kwargs.get("display", False):
            return title
        else:
            return Markup("<!-- %s -->" % title)

def title(macro, environ, context, *args, **kwargs):
    """Renders the current title of the page
    
    **Arguments:** //None//

    **Example(s):**
    {{{
    <<title>>
    }}}
    """

    return context.get("title", context.get("page", None)["name"])

def add_comment(macro, environ, context, *args, **kwargs):
    """..."""

    # Setup info and defaults
    parser = environ.parser
    request = environ.request

    user = environ._user()

    page = context["page"]
    page_name = page["name"]
    page_text = page["text"]
    
    # Can this user add a comment to this page?
    appendonly = ("appendonly" in args)

    # Get the data from the POST
    comment = request.kwargs.get("comment", "")
    action = request.kwargs.get("action", "")
    
    # Ensure <<add-comment>> is not present in comment, so that infinite
    # recursion does not occur.
    comment = re.sub("(^|[^!])(\<\<add-comment)", "\\1!\\2", comment)
    
    the_preview = None
    the_comment = None

    # If we are submitting or previewing, inject comment as it should look
    if action == "preview":
        the_preview = tag.div(tag.h1("Preview"), id="preview")
        the_preview += tag.div(parser.generate(comment,
            environ=(environ, context)), class_="article")

    # When submitting, inject comment before macro
    if comment and action == "save":
        new_text = ""
        comment_text = "==== Comment by %s on %s ====\n%s\n\n" % (
                user, time.strftime('%c', time.localtime()), comment)
        for line in page_text.split("\n"):
            if line.find("<<add-comment") == 0:
                new_text += comment_text
            new_text += line + "\n"

        search = environ.search
        storage = environ.storage

        storage.reopen()
        search.update(environ)

        storage.save_text(page_name, new_text, user,
                "Comment added by %s" % user)

        search.update_page(environ.get_page(page_name), page_name,
                text=new_text)

        the_comment = parser.generate(comment_text,
                environ=(environ, context))

    the_form = tag.form(
            tag.input(type="hidden", name="parent", value=page["node"]),
            tag.fieldset(
                tag.legend("Add Comment"),
                tag.p(
                    tag.textarea(
                        (not action in ("cancel", "save") and comment or ""),
                        id="comment",
                        name="comment",
                        cols=80, rows=5
                    ),
                    class_="text"
                ),
                tag.h4(tag.label("Your email or username:", for_="author")),
                tag.p(
                    tag.input(id="author", name="author", type="text"),
                    class_="input"
                ),
                tag.p(
                    tag.button("Preview", type="submit",
                        name="action", value="preview"),
                    tag.button("Save", type="submit",
                        name="action", value="save"),
                    tag.button("Cancel", type="submit",
                        name="action", value="cancel"),
                    class_="button"
                ),
            ),
            method="post", action=""
    )

    return tag(the_preview, the_comment, the_form)
