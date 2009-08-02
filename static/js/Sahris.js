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

String.implement({
    parseQueryString: function () {
        var vars = this.split(/[&;]/), res = {};
        if (vars.length) vars.each(function(val){
            var index = val.indexOf("="),
                keys = index < 0 ? [""] : val.substr(0,
                    index).match(/[^\]\[]+/g),
                value = decodeURIComponent(val.substr(index + 1)),
                obj = res;
            keys.each(function(key, i){
                var current = obj[key];
                if(i < keys.length - 1)
                    obj = obj[key] = current || {};
                else if($type(current) == "array")
                    current.push(value);
                else
                    obj[key] = $defined(current) ? [current, value] : value;
            });
        });
        return res;
    },

    cleanQueryString: function(method) {
        return this.split("&").filter(function (val) {
            var index = val.indexOf("="),
            key = index < 0 ? "" : val.substr(0, index),
            value = val.substr(index + 1);
            return method ? method.run([key, value]) : $chk(value);
        }).join("&");
    }
});

Native.implement([Events, Element, Window, Document], {
    on: function (type, fn) {
        this.addEvent(type, fn);
    },

    fire: function (type, args) {
        this.fireEvent(type, args);
    },

    un: function (type, fn) {
        this.removeEvent(type, fn);
    }
});

Element.implement({

    isDisplayed: function () {
        return this.getStyle("display") !== "none";
    },

    toggle: function () {
        return this[this.isDisplayed() ? "hide" : "show"]();
    },

    hide: function () {
        var d;
        try {
            //IE fails here if the element is not in the dom
            if ("none" !== this.getStyle("display")) {
                d = this.getStyle("display");
            }
        } catch (e) {
        }

        return this.store("originalDisplay", d || "block").setStyle(
            "display", "none");
    },

    show: function (display) {
        return this.setStyle("display", display || this.retrieve(
                    "originalDisplay") || "block");
    },

    swapClass: function (remove, add) {
        return this.removeClass(remove).addClass(add);
    },

    setLabel: function(attr)    {
        var label;
        attr = attr || "alt";
        label = this.getProperty(attr);
        if ($defined(label)) {
            this.addEvents({
                "focus": function() {
                    if (this.get("value").clean() == label) {
                        this.set("value", "").removeClass("helpOn");
                    }
                },
                "blur": function()  {
                    var value = this.get("value").clean();
                    if (value == "" || value == label) {
                        this.set("value", label).addClass("helpOn");
                    }
                }
            }).fireEvent("blur");
        }
        return this.removeProperty(attr);
    },

    resize: function (w, h) {
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

if (!$defined(Sahris)) {
    var Sahris = {};
}

Sahris.Plugin = new Class({
    Extends: Component,

    templates: {
        error: "<h1>Error</h1><div class=\"system-message\"><p class=\"error\">{error}</p></div>",
        message: "<h1>Message</h1><div class=\"system-message\"><p class=\"message\">{message}</p></div>"
    },

    initialize: function (ui) {
        this.ui = ui;
    },

    setError: function (node, error) {
        $(node).set("html", this.templates.error.substitute({
            error: error}));
    },

    setMessage: function (node, message) {
        $(node).set("html", this.templates.message.substitute({
            message: message}));
    },

    run: function (node, data) {
        this.setError(node, "Plugin " + name + " not implemented");
    }
});

Sahris.Plugins = {};

Sahris.Manager = new Class({
    Extends: Component,

    templates: {
        error: "<h1>Error</h1><div class=\"system-message\"><p class=\"message\">{message}</p></div>"
    },

    plugins: new Hash(),

    initialize: function (app) {
        this.app = app;

        this.app.on("plugin", this.onPlugin.bind(this));

        for (name in Sahris.Plugins) {
            this.plugins.set(name, new Sahris.Plugins[name](this.app.ui));
        }
    },

    onPlugin: function (name, node, data) {
        var plugin = this.plugins.get(name);
        if (plugin) {
            plugin.run(node, data);
        } else {
            $(node).set("html", this.templates.error.substitute({
                message: "Plugin \"" + name + "\" not found!"}));
        }
    }
});

Sahris.App = new Class({
    Extends: Component,

    initialize: function () {
        this.ui = new Sahris.UI();

        this.ui.on("plugin", function () {
            this.fire("plugin", arguments);
        }.bind(this));

        this.ui.load();
    }
});

Sahris.Template = new Class({
    Extends: Component,

    initialize: function (el, url) {
        this.el = el;
        this.url = url;
    },

    load: function () {
        this.el.set("load", {
            "onSuccess": function (responseText, responseXML) {
                this.fire("loaded");
            }.bind(this),
            "onFailure": function (xhr) {
                this.fire("failed", [xhr.status, xhr.statusText]);
            }.bind(this)
        }).load(this.url);
    }
});

Sahris.UI = new Class({
    Extends: Component,

    templates: {
        error: "<h1>Error</h1><p class=\"message\">{message}</p>",
        meta: "<p>Last edited by {author} (Revision: {rev}) {date}</p>"
    },

    editing: false,
    viewing: true,

    initialize: function () {
        this.addEvents({
            "historyChanged": this.onHistoryChanged.bind(this)
        });

        this.el = $(document.body);
        this.url = "/templates/base.xhtml";
        this.tpl = new Sahris.Template(this.el, this.url);
        this.tpl.on("loaded", this.onTplLoaded.bind(this));
        this.tpl.on("failed", this.onTplFailed.bind(this));

        this.historyKey = "Sahris.UI";

        this.menu = null;
    },

    onButtonClicked: function (e) {
        var hash;

        if (e.target.get("text") === "Save") {
            this.doSave();
        } else if (e.target.get("text") === "Cancel") {
            this.doEdit(false);
            this.setStatus("Cancelled");

            hash = "{name}".substitute({name: this.page.name});
            this.history.setValue(0, hash);
        } else {
            hash = e.target.href;
            hash = hash.replace(/^.*#/, "");
            this.history.setValue(0, hash);
        }

        e.preventDefault();
    },

    onKeyPressed: function (e) {
        if (e.code === 27) {
            if (this.editing) {
                this.doEdit(false);
                this.setStatus("Cancelled");

                var hash = "{name}".substitute({name: this.page.name});
                this.history.setValue(0, hash);
            }
        }
    },

    onLinkClicked: function (e) {
        var hash = e.target.href;
        hash = hash.replace(/^.*#/, "");
        this.history.setValue(0, hash);
        e.preventDefault();
    },

    onTplLoaded: function () {
        this.menu = new Sahris.Menu(this.el.getElement("#menu"), "SiteMenu");
        this.menu.load();

        this.el.getElements("#metanav a").on("click",
            this.onLinkClicked.bind(this));

        this.el.getElements("#ctxnav a").on("click",
            this.onLinkClicked.bind(this));

        this.el.getElements("#buttons a").on("click",
            this.onButtonClicked.bind(this));

        this.el.getElements("#content").on("dblclick", function () {
            this.history.setValue(0, "{name}?action=edit".substitute(
                {name: this.page.name}));
        }.bind(this));

        $(document).on("keypress", this.onKeyPressed.bind(this));

        this.search = new Sahris.Search(this.el.getElement("#search"));
        this.search.on("search", function (q) {
            this.history.setValue(0, "Search?q=" + q);
        }.bind(this));

        this.editor = new Sahris.Editor(this.el.getElement("#editor"));
        this.editor.on("plugin", function () {
            this.fire("plugin", arguments);
        }.bind(this));

        var uri, contentEl, pageEl;

        // Resize Editor appropriately
        contentEl = this.el.getElement("#content");
        this.editor.textEl.resize(
            contentEl.getWidth() - contentEl.getStyle("padding-right").toInt(),
            contentEl.getHeight() - 
            contentEl.getStyle("padding-bottom").toInt());

        pageEl = this.el.getElement("#content > #page");
        this.page = new Sahris.Page(pageEl, "/wiki", Sahris.config.frontpage);
        this.page.on("loaded", this.onPageLoaded.bind(this));
        this.page.on("error", this.onPageError.bind(this));
        this.page.on("saved", this.onPageSaved.bind(this));
        this.page.on("linkClicked", this.onLinkClicked.bind(this));

        this.page.on("plugin", function () {
            this.fire("plugin", arguments);
        }.bind(this));

        this.history = HistoryManager.register(this.historyKey, [1],
            function (values) {
                this.fire("historyChanged", [values]);
            }.bind(this),
            function (values) {
                this.fire("historyChanged", [values]);
                return values;
            }.bind(this),
            "(.*)");
        HistoryManager.start();

        if (Cookie.read("signature") === null) {
            Cookie.write("signature", "AnonymousUser", {
                domain: location.host,
                duration: 90
            });
        }

        this.el.getElement("#software #sahris span.version").set("text",
                Sahris.version);

        $(document.head).getElement("title").set(
                "html", Sahris.config.sitename);

        this.fire("loaded");
    },
    
    onHistoryChanged: function (values) {
        var parts, name, query, action;
        if ($defined(this.page)) {
            name = Sahris.config.frontpage;
            action = "view";
            query = {};

            if (values && values[0]) {
                parts = values[0].split("?");
                name = parts[0];
                if (parts.length == 2) {
                    query = parts[1].parseQueryString();
                }
                action = query.action || "view";
            }

            if (action === "edit") {
                this.editing = true;
                this.viewing = false;
            } else {
                if (this.editing) {
                    this.doEdit(false);
                }
                this.viewing = true;
                this.editing = false;
            }

            if (this.page.name !== name) {
                this.page.load(name, query);
            } else {
                this.page.fire("loaded");
            }
        }
    },

    onTplFailed: function (status, statusText) {
        this.fire("failed", [status, statusText]);
    },

    onPageLoaded: function () {
        if (this.viewing) {
            this.page.render();
            this.setTitle(this.page.name || this.page.title);

            this.setStatus(this.templates.meta.substitute({
                author: this.page.author,
                rev: this.page.rev,
                date: new Date(this.page.date * 1000).pretty()
            }));
        } else {
            this.doEdit(true);
            this.setTitle("Editing {name}".substitute({name: this.page.name}));
        }

        if (this.page.name) {
            this.menu.setActive(this.page.name);
        }
        if (this.page.name) {
            this.el.getElement("#ctxnav a#history").set("href",
                "#History?name=" + this.page.name);
            this.el.getElements("#buttons a:first-child").set("href",
                "#{name}?action=edit".substitute({name: this.page.name}));
        }
    },

    onPageError: function (status, statusText) {
        if (($type(status) === "boolean") && !(status)) {
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

    onPageSaved: function (message) {
        this.doEdit(false);
        this.setStatus(message);

        var hash = "{name}".substitute({name: this.page.name});
        this.history.setValue(0, hash);

        this.page.fire("loaded");
    },

    load: function () {
        this.tpl.load();
    },

    doEdit: function (flag) {
        var buttons;
        if (($type(flag) === "boolean") && !(flag)) {
            this.editing = false;
            this.viewing = true;
            this.editor.hide();
            this.page.show();
            this.setTitle(this.page.name);
            buttons = this.el.getElements("#buttons a");
            buttons[0].set("text", "Edit");
            buttons[1].set("text", "More...");
        } else {
            this.page.hide();
            this.editor.load(this.page);
            this.editor.show();
            buttons = this.el.getElements("#buttons a");
            buttons[0].set("text", "Save");
            buttons[1].set("text", "Cancel");
        }
    },

    doSave: function () {
        this.editor.update(this.page);
        this.page.save();
    },

    clearError: function () {
        if (this.el.getElement("#content").hasClass("error")) {
            this.el.getElement("#content").removeClass("error");
            this.el.getElement("#content").addClass("content");
            this.el.getElement("#page").addClass("wiki");
        }
    },

    setError: function (message) {
        if (this.el.getElement("#content").hasClass("content")) {
            this.el.getElement("#content").removeClass("content");
            this.el.getElement("#content").addClass("error");
        }
        this.setStatus("");
        this.page.el.set("html",
            this.templates.error.substitute(
                {message: message}));
    },

    setStatus: function (message) {
        this.el.getElement("#status").set("html", message);
    },

    setTitle: function (title) {
        var titleEl = this.el.getElement("#title ");
        titleEl.getElement("#backlink").set("href",
                "#BackLinks?name=" + title);
        titleEl.getElement("#backlink").set("text", title);
    }
});

Sahris.Page = new Class({
    Extends: Component,

    initialize: function (el, baseurl, defaultPage) {
        this.el = el;
        this.baseurl = baseurl;
        this.defaultPage = defaultPage;

        this.addEvents({
            "loaded": this.onLoaded.bind(this)
        });

        this.parser = new Sahris.Parser();
        this.parser.on("plugin", function () {
            this.fire("plugin", arguments);
        }.bind(this));

        this.clear();
    },

    onLinkClicked: function (e) {
        this.fire("linkClicked", e);
    },

    hide: function () {
        this.el.hide();
    },

    show: function () {
        this.el.show();
    },

    clear: function () {
        this.name = "";
        this.text = "";
        this.rev = 0;
        this.author = "";
        this.comment = "";
    },

    load: function (name, options) {
        var url, jsonRequest;

        this.clear();
        this.name = name;

        url = "{baseurl}/{name}".substitute({
            baseurl: this.baseurl,
            name: name
        });

        jsonRequest = new Request.JSON({
            url: url,
            onSuccess: function (responseJSON, responseText) {
                var o = responseJSON;
                if (o.success) {
                    $extend(this, o.data);
                    this.fire("loaded", this);
                } else {
                    this.fire("error", [o.success, o.message]);
                }
            }.bind(this),
            "onFailure": function (xhr) {
                this.fire("error", [xhr.status, xhr.statusText]);
            }.bind(this)
        });
        jsonRequest.get(options);
    },

    save: function () {
        var url, data, jsonRequest;

        url = "{baseurl}/{name}".substitute({
            baseurl: this.baseurl,
            name: this.name
        });

        data = {
            text: this.text,
            author: this.author,
            comment: this.comment
        };

        jsonRequest = new Request.JSON({
            url: url,
            data: JSON.encode(data),
            urlEncoded: false,
            onSuccess: function (responseJSON, responseText) {
                var o = responseJSON;
                if (o.success) {
                    this.fire("saved", o.message);
                } else {
                    this.fire("error", [true, o.message]);
                }
            }.bind(this),
            "onFailure": function (xhr) {
                this.fire("error", [xhr.status, xhr.statusText]);
            }.bind(this)
        });
        jsonRequest.post();
    },

    render: function () {
        this.el.empty();
        this.parser.parse(this.el, this.text);
    },

    onLoaded: function () {
        this.el.getElements("a").on("click", this.onLinkClicked.bind(this));
    }
});

Sahris.Menu = new Class({
    Extends: Component,

    initialize: function (el, defaultPage) {
        this.el = el;
        this.defaultPage = defaultPage;

        this.page = new Sahris.Page(this.el, "/wiki", this.defaultPage);
        this.page.on("loaded", this.onPageLoaded.bind(this));
        this.page.on("failed", this.onPageError.bind(this));

        this.clear();
    },

    onPageLoaded: function () {
        this.page.render();
        this.fire("loaded");
    },

    onPageError: function (status, statusText) {
        this.fire("failed", [status, statusText]);
    },

    clear: function () {
        this.el.empty();
    },

    load: function () {
        this.clear();
        this.page.load(this.defaultPage);
    },

    setActive: function (name) {
        var el;

        el = this.el.getElement("li.active");
        if ($defined(el)) {
            el.removeClass("active");
        }

        el = this.el.getElement("li a[href$=\"{name}\"]".substitute(
            {name: name}));
        if ($defined(el)) {
            el.getParent().addClass("active");
        }
    }
});

Sahris.Parser = new Class({
    Extends: Component,
    Implements: Options,

    options: {
        interwiki: {
            MeatBall: "http://www.usemod.com/cgi-bin/mb.pl?"
        },
        linkFormat: "#"
    },

    initialize: function (options) {
        this.setOptions(options);
        this.creole = new Parse.Simple.Creole(this.options);
        this.creole.options.plugin = this.plugin.bind(this);
    },

    plugin: function (node, r, options) {
        this.fire("plugin", [node, r, options]);
    },

    parse: function (el, text) {
        this.creole.parse(el, text);
    }
});

Sahris.Editor = new Class({
    Extends: Component,

    initialize: function (el) {
        this.el = el;
        this.textEl = this.el.getElement("#editor-content textarea");
        this.commentEl = this.el.getElement("#editor-fields [name=comment]");
        this.commentEl.setLabel();

        this.parser = new Sahris.Parser();
        this.parser.on("plugin", function () {
            this.fire("plugin", arguments);
        }.bind(this));

        var panel = {
            preview: $("preview"),
            output: null,
            input: $("text")
        };
        this.wmdPreviewManager = new mooWMD.PreviewMgr(panel, this.parser);
        this.wmdEditor = new mooWMD.Editor(panel.input,
            this.wmdPreviewManager.refresh.bind(this.wmdPreviewManager), "");
    },

    load: function (page) {
        this.textEl.set("value", page.text);
    },

    update: function (page) {
        page.text = this.textEl.get("value") || "";
        page.rev += 1;
        page.date = $time();
        page.author = Cookie.read("signature") || "AnonymousUser";
        page.comment = this.commentEl.get("value") || "";
    },

    hide: function () {
        this.el.hide();
    },

    show: function () {
        this.el.show();
    }
});

Sahris.Search = new Class({
    Extends: Component,

    initialize: function (el) {
        this.el = el;
        this.qEl = this.el.getElement("#q");
        this.qEl.setLabel();
        this.searchBtnEl = this.el.getElement("#searchBtn");

        this.el.getElement("#searchForm").on("submit", function (e) {
            e.preventDefault();
            this.search(this.qEl.get("value"));
        }.bind(this));
        this.el.getElement("#searchBtn").on("click", function (e) {
            e.preventDefault();
            this.search(this.qEl.get("value"));
        }.bind(this));
    },

    search: function (q) {
        this.fire("search", q);
    }
});

$(document).on("domready", function () {
    Sahris.app = new Sahris.App();
    Sahris.manager = new Sahris.Manager(Sahris.app);
    Sahris.app.on("plugin", function () {
        Sahris.manager.fire("plugin", arguments);
    });
});
