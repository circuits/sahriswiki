"""Wiki macros"""

import re
import time

from genshi.builder import tag

def title(macro, environ, *args, **kwargs):
    """Return the title of the current page."""

    return environ.page["name"]

def add_comment(macro, environ, *args, **kwargs):
    """..."""

    # Prevent multiple inclusions - store a temp in environ
    if "add-comment" in environ.tmp:
        raise Exception("<<add-comment>> macro cannot be included twice.")
    environtmp["add-comment"] = True

    # Setup info and defaults
    parser = environ.parser
    request = environ.request

    user = request.remote.ip

    page = environ.page
    page_name = page["name"]
    page_text = page["text"]
    page_url = page["url"]
    
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
        the_preview += tag.div(parser.generate(comment, environ=environ),
                class_="article")

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
        search.update()

        storage.save_text(page_name, new_text, user,
                "Comment added by %s" % user)

        search.update_page(page_name, text=new_text)

        the_comment = parser.generate(comment_text, environ=environ)

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
