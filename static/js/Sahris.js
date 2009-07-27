/*
 * Sahris
 *
 * @author      James Mills, prologic at shortcircuit dot net dot au
 * @copyright   (C) 2009, SoftCircuit (James Mills)
 * @date        8th July 2009
 *
 * @license     MIT (See LICENSE file in source distribution)
 */

//
// mootools Enhancements
//

Native.implement([Events, Element, Window, Document], {
    on: function(type, fn) {
        this.addEvent(type, fn);
    },

    fire: function(type, args) {
        this.fireEvent(type, args);
    },

    un: function(type, fn) {
        this.removeEvent(type, fn);
    }
});

Element.implement({

    isDisplayed: function(){
        return this.getStyle('display') != 'none';
    },

    toggle: function(){
        return this[this.isDisplayed() ? 'hide' : 'show']();
    },

    hide: function(){
        var d;
        try {
            //IE fails here if the element is not in the dom
            if ('none' != this.getStyle('display')) d = this.getStyle('display');
        } catch(e){}

        return this.store('originalDisplay', d || 'block').setStyle('display', 'none');
    },

    show: function(display){
        return this.setStyle('display', display || this.retrieve('originalDisplay') || 'block');
    },

    swapClass: function(remove, add){
        return this.removeClass(remove).addClass(add);
    }

});

Element.implement({
    resize: function(w, h) {
        this.setStyles({
            "width": w,
            "height": h
        });
        this.fireEvent("resize");
    }
});

var Component = new Class({
    Extends: Events
});

//
// Sahris
//

var Sahris = {
    version: "0.1"
};

Sahris.App = new Class({
    Extends: Component,

    initialize: function() {
        this.ui = new Sahris.UI();
    },

    run: function() {
        this.ui.load();
    }
});

Sahris.Template = new Class({
    Extends: Component,

    initialize: function(el, url) {
        this.el = el;
        this.url = url;

        this.addEvents({
            "loaded": this.onLoaded.bind(this),
            "failed": this.onFailed.bind(this)
        });
    },

    load: function() {
        this.el.set("load", {
            "onSuccess": function(responseText, responseXML) {
               this.fire("loaded");
            }.bind(this),
            "onFailure": function(xhr) {
                this.fire("failed", [xhr.status, xhr.statusText]);
            }.bind(this)
        }).load(this.url);
    },

    onLoaded: function() {
    },

    onFailed: function(status, statusText) {
    }
});

Sahris.UI = new Class({
    Extends: Component,

    templates: {
        error: "<h1>Error</h1><p class=\"message\">{message}</p>",
        meta: "<p>Last edited by {author} (Revision: {rev}) " +
            "about {date}</p>"
    },

    editing: false,
    viewing: true,

    initialize: function() {
        this.addEvents({
            "loaded": this.onLoaded.bind(this),
            "failed": this.onFailed.bind(this)
        });

        this.el = $(document.body);
        this.url = "/templates/base.xhtml";
        this.tpl = new Sahris.Template(this.el, this.url);
        this.tpl.on("loaded", this._onTplLoaded.bind(this));
        this.tpl.on("failed", this._onTplFailed.bind(this));

        this.historyKey = "Sahris.UI";

        this.menu = null;
    },

    _onButtonClicked: function(e) {
        e.preventDefault();

        if (e.target.get("text") == "Save") {
            this.doSave();
        } else if (e.target.get("text") == "Cancel") {
            this.doEdit(false);
            this.setStatus("Cancelled");

            var hash = "#{name}".substitute({name: this.page.name});
            this.history.setValue(0, hash);

            this.page.fire("loaded");
        } else {
            var hash = e.target.href;
            if (hash && hash[0] == "#") {
                hash = hash.replace(/^.*#/, "");
                this.history.setValue(0, hash);
            }
        }
    },

    _onKeyPressed: function(e) {
        if (e.code == 27) {
            if (this.editing) {
                this.doEdit(false);
                this.setStatus("Cancelled");

                var hash = "#{name}".substitute({name: this.page.name});
                this.history.setValue(0, hash);

                this.page.fire("loaded");
            }
        }
    },

    _onLinkClicked: function(e) {
        e.preventDefault();
        var hash = e.target.href;
        if (hash && hash[0] == "#") {
            hash = hash.replace(/^.*#/, "");
            this.history.setValue(0, hash);
        }
    },

    _onTplLoaded: function() {
        this.el.getElements("#metanav a").on("click",
            this._onLinkClicked.bind(this));

        this.el.getElements("#ctxnav a").on("click",
            this._onLinkClicked.bind(this));

        this.el.getElements("#buttons a").on("click",
            this._onButtonClicked.bind(this));

        this.el.getElements("#content").on("dblclick", function() {
            this.history.setValue(0, "#{name}/edit".substitute(
                {name: this.page.name}));
            this.doEdit(true);
        }.bind(this));

        $(document).on("keypress", this._onKeyPressed.bind(this));

        this.editor = new Sahris.Editor(this.el.getElement("#editor"));

        // Resize Editor appropriately
        console.log("Resizing Editor");
        var contentEl = this.el.getElement("#content");
        var dimensions = contentEl.getComputedSize();
        this.editor.textEl.resize(
            dimensions.width - dimensions["padding-right"],
            dimensions.height - dimensions["padding-bottom"]);

        var pageEl = this.el.getElement("#content > #page");
        this.page = new Sahris.Page(pageEl, "/wiki", "FrontPage");
        this.page.on("loaded", this._onPageLoaded.bind(this));
        this.page.on("error", this._onPageError.bind(this));
        this.page.on("saved", this._onPageSaved.bind(this));
        this.page.on("linkClicked", this._onLinkClicked.bind(this));

        this.history = HistoryManager.register(this.historyKey, [1],
            function(values) {
                if ($defined(this.page)) {
                    if (values && values[0]) {
                        var parts = values[0].split("/");
                        if (parts.length == 2) {
                            var name = parts[0], action = parts[1];
                        } else {
                            var name = parts[0], action = "view";
                        }
                    } else {
                        var name = "FrontPage", action = "view";
                    }

                    if (action == "edit") {
                        this.editing = true;
                        this.viewing = false;
                    } else {
                        this.viewing = true;
                        this.editing = false;
                    }

                    if (this.page.name != name) {
                        this.page.load(name);
                    }
                }
            }.bind(this),
            function(values) {
                return values;

            }.bind(this),
            "(.*)");
        HistoryManager.start();

        this.fire("loaded");
    },

    _onTplFailed: function(status, statusText) {
        this.fire("failed", [status, statusText]);
    },

    _onPageLoaded: function() {
        if (this.viewing) {
            this.page.render();
            this.setTitle(this.page.name || this.page.title);
        } else {
            this.doEdit(true);
            this.setTitle("Editing {name}".substitute({name: this.page.name}));
        }

        if (this.page.name) {
            this.menu.setActive(this.page.name);
        }
        if (this.page.name) {
            this.el.getElement("#ctxnav a#history").set("href",
                "#History/" + this.page.name);
            this.el.getElements("#buttons a:first-child").set("href",
                "#{name}/edit".substitute({name: this.page.name}));
        }
    },

    _onPageError: function(status, statusText) {
        if (($type(status) == "boolean") && !(status)) {
            this.setError(statusText);
            this.setTitle(this.page.name);
            this.menu.setActive(this.page.name);
        } else {
            this.setError("{status} {statusText}".substitute({
                status: status,
                statusText: statusText
            }));
        }
    },

    _onPageSaved: function(message) {
        this.doEdit(false);
        this.setStatus(message);

        var hash = "#{name}".substitute({name: this.page.name});
        this.history.setValue(0, hash);

        this.page.fire("loaded");
    },

    load: function() {
        this.tpl.load();
    },

    doEdit: function(flag) {
        if (($type(flag) == "boolean") && !(flag)) {
            this.editing = false;
            this.viewing = true;
            this.editor.hide();
            this.page.show();
            this.setTitle(this.page.name);
            var buttons = this.el.getElements("#buttons a");
            buttons[0].set("text", "Edit");
            buttons[1].set("text", "More...");
        } else {
            this.page.hide();
            this.editor.load(this.page);
            this.editor.show();
            var buttons = this.el.getElements("#buttons a");
            buttons[0].set("text", "Save");
            buttons[1].set("text", "Cancel");
        }
    },

    doSave: function() {
        this.editor.update(this.page);
        this.page.save();
    },

    clearError: function() {
        if (this.el.getElement("#content").hasClass("error")) {
            this.el.getElement("#content").removeClass("error");
            this.el.getElement("#content").addClass("content");
            this.el.getElement("#page").addClass("wiki");
        }
    },

    setError: function(message) {
        if (this.el.getElement("#content").hasClass("content")) {
            this.el.getElement("#content").removeClass("content");
            this.el.getElement("#content").addClass("error");
        }
        this.page.el.set("html",
            this.templates.error.substitute(
                {message: message}));
    },

    setStatus: function(message) {
        this.el.getElement("#status").set("html", message);
    },

    setTitle: function(title) {
        this.el.getElement("#title").set("html", title);
    },

    onLoaded: function() {
        if (this.menu == null) {
            this.menu = new Sahris.Menu(
                this.el.getElement("#menu"),
                "SiteMenu");
        }
        this.menu.load();
    },

    onFailed: function(status, statusText) {
    }
});

Sahris.Page = new Class({
    Extends: Component,

    initialize: function(el, baseurl, defaultPage) {
        this.el = el;
        this.baseurl = baseurl;
        this.defaultPage = defaultPage;

        this.addEvents({
            "loaded": this.onLoaded.bind(this),
            "saved": this.onSaved.bind(this),
            "error": this.onError.bind(this)
        });

        this.parser = new Sahris.Parser();

        this.clear();
    },

    _onLinkClicked: function(e) {
        this.fire("linkClicked", e);
    },

    hide: function() {
        this.el.hide();
    },

    show: function() {
        this.el.show();
    },

    clear: function() {
        this.name = "";
        this.text = "";
        this.rev = 0;
        this.author = "";
        this.comment = "";
    },

    load: function(name) {
        this.clear();
        this.name = name;

        var url = "{baseurl}/{name}".substitute({
            baseurl: this.baseurl,
            name: name
        });

        var jsonRequest = new Request.JSON({
            url: url,
            onSuccess: function(responseJSON, responseText) {
                var o = responseJSON;
                if (o.success) {
                    $extend(this, o.data);
                    this.fire("loaded", this);
                } else {
                    this.fire("error", [o.success, o.message]);
                }
            }.bind(this),
            "onFailure": function(xhr) {
                this.fire("error", [xhr.status, xhr.statusText]);
            }.bind(this)
        });
        jsonRequest.get();
    },

    save: function() {
        var url = "{baseurl}/{name}".substitute({
            baseurl: this.baseurl,
            name: this.name
        });

        var data = {
            text: this.text,
            author: this.author,
            comment: this.comment
        };

        var jsonRequest = new Request.JSON({
            url: url,
            data: JSON.encode(data),
            urlEncoded: false,
            onSuccess: function(responseJSON, responseText) {
                var o = responseJSON;
                if (o.success) {
                    this.fire("saved", o.message);
                } else {
                    this.fire("error", [true, o.message]);
                }
            }.bind(this),
            "onFailure": function(xhr) {
                this.fire("error", [xhr.status, xhr.statusText]);
            }.bind(this)
        });
        jsonRequest.post();
    },

    render: function() {
        this.el.empty()
        this.parser.parse(this.el, this.text);
    },

    onLoaded: function() {
        this.el.getElements("a").on("click", this._onLinkClicked.bind(this));
    },

    onFailed: function(status, statusText) {
    },

    onSaved: function() {
    },

    onError: function(status, statusText) {
    }
});

Sahris.Menu = new Class({
    Extends: Component,

    initialize: function(el, defaultPage) {
        this.el = el;
        this.defaultPage = defaultPage;

        this.addEvents({
            "loaded": this.onLoaded.bind(this),
            "failed": this.onFailed.bind(this)
        });

        this.page = new Sahris.Page(this.el, "/wiki", this.defaultPage);
        this.page.on("loaded", this._onPageLoaded.bind(this));
        this.page.on("failed", this._onPageError.bind(this));

        this.clear();
    },

    _onPageLoaded: function() {
        this.page.render();
        this.fire("loaded");
    },

    _onPageError: function(status, statusText) {
        this.fire("failed", [status, statusText]);
    },

    clear: function() {
        this.el.empty();
    },

    load: function() {
        this.clear();
        this.page.load(this.defaultPage);
    },

    setActive: function(name) {
        var el = this.el.getElement("li.active");
        if ($defined(el)) {
            el.removeClass("active");
        }

        var el = this.el.getElement("li a[href$=\"{name}\"]".substitute(
            {name: name}));
        if ($defined(el)) {
            el.getParent().addClass("active");
        }
    },

    onLoaded: function() {
    },

    onFailed: function(status, statusText) {
    }
});

Sahris.Parser = new Class({
    Implements: Options,

    options: {
        interwiki: {
            MeatBall: "http://www.usemod.com/cgi-bin/mb.pl?"
        },
        linkFormat: "#"
    },

    initialize: function(options) {
        this.setOptions(options);
        this.creole = new Parse.Simple.Creole(this.options);
    },

    parse: function(el, text) {
        this.creole.parse(el, text);
    }
});

Sahris.Editor = new Class({
    Extends: Component,

    initialize: function(el) {
        this.el = el;
        this.textEl = this.el.getElement("#editor-content textarea");
        this.commentEl = this.el.getElement("#editor-fields [name=comment]");

        new OverText(this.commentEl).show();
    },

    load: function(page) {
        this.textEl.set("value", page.text);
    },

    update: function(page) {
        page.text = this.textEl.get("value");
        page.comment = this.commentEl.get("value")[0];
    },

    hide: function() {
        this.el.hide();
    },

    show: function() {
        this.el.show();
    }
});

$(document).on("domready", function() {
    new Sahris.App().run();
});
