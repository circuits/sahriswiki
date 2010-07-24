# Module:   wiki
# Date:     12th July 2010
# Author:   James Mills, prologic at shortcircuit dot net dot au

"""Wiki Macros

Various wiki and page macros.
"""

import re
import time

from genshi.builder import tag
from genshi.core import Markup
from genshi.output import HTMLSerializer

serializer = HTMLSerializer()

def SetTitle(macro, environ, data, *args, **kwargs):
    """Set the title of the page.
    
    This macro allows you to set a custom title for a page that is
    different to the name of the page (//for SEO purposes//). You can
    also optinoally specify that you also want the newly set title
    to be rendered in-place.

    **Arguments:**
    * title (//the new title//)
    * display=False (//whether to render the title//)

    **Example(s):**
    {{{
    <<SetTitle "My Title">>
    }}}

    <<SetTitle "SahrisWiki Macros">>

    {{{
    <<SetTitle "My Title", display=True>>
    }}}

    <<SetTitle "SahrisWiki Macros", display=True>>
    """

    title = kwargs.get("title", (args and args[0]) or u"")
    display = kwargs.get("display", False)

    if not title:
        return None

    data["title"] = title

    if display:
        return title
    else:
        return Markup("<!-- %s -->" % title)

def title(macro, environ, data, *args, **kwargs):
    """Displays the current title of the page or it's name.
    
    This macro simply displays the title or name of the current page.

    **Arguments:** //No Arguments//

    **Example(s):**
    {{{
    <<title>>
    }}}

    <<title>>
    """

    if "title" in data:
        title = data["title"]
    elif "page" in data:
        title = data["page"].get("name", u"")
    else:
        title = u""

    return title

def AddComment(macro, environ, data, *args, **kwargs):
    """Display an add comment form allowing users to post comments.

    This macro allows you to display an add comment form on the current
    page allowing users to post comments. The comments are added to the
    page's content itself.
    
    **Arguments:** //No Arguments//

    **Example(s):**
    {{{
    <<AddComment>>
    }}}

    <<AddComment>>
    """

    # Setup info and defaults
    parser = environ.parser
    request = environ.request

    page = data["page"]
    page_name = page["name"]
    page_text = page["text"]
    
    # Get the data from the POST
    comment = request.kwargs.get("comment", "")
    action = request.kwargs.get("action", "")
    author = request.kwargs.get("author", environ._user())
    
    # Ensure <<add-comment>> is not present in comment, so that infinite
    # recursion does not occur.
    comment = re.sub("(^|[^!])(\<\<add-comment)", "\\1!\\2", comment)
    
    the_preview = None
    the_comment = None

    # If we are submitting or previewing, inject comment as it should look
    if action == "preview":
        the_preview = tag.div(tag.h1("Preview"), id="preview")
        the_preview += tag.div(parser.generate(comment, context="inline",
            environ=(environ, data)), class_="article")

    # When submitting, inject comment before macro
    if comment and action == "save":
        new_text = ""
        comment_text = "==== Comment by %s on %s ====\n%s\n\n" % (
                author, time.strftime('%c', time.localtime()), comment)
        for line in page_text.split("\n"):
            if line.find("<<add-comment") == 0:
                new_text += comment_text
            new_text += line + "\n"

        search = environ.search
        storage = environ.storage

        storage.reopen()
        search.update(environ)

        storage.save_text(page_name, new_text, author,
                "Comment added by %s" % author)

        search.update_page(environ.get_page(page_name), page_name,
                text=new_text)

        the_comment = parser.generate(comment_text, context="inline",
                environ=(environ, data))

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

def source(macro, environ, data, *args, **kwargs):
    """Display the HTML source of some parsed wiki text
    
    This macro allows you to display the genereated HTML source of some
    parsed wiki text. (//Useful mostly for debugging//).

    **Arguments:** //No Arguments//

    **Example(s):**
    {{{
    <<source>>**Hello World!**<</source>>
    }}}

    <<source>>**Hello World!**<</source>>
    """

    if not macro.body:
        return None

    contents = environ.parser.generate(macro.body, context="inline",
            environ=(environ, data))
    
    return tag.pre("".join(serializer(contents)))
