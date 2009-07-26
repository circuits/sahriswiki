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

var Component = new Class({
    Extends: Events,
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
        console.log("Sahris.App initializing...");
        this.ui = new Sahris.UI();
    },

    run: function() {
        console.log("Sahris.App running...");
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
        console.log("Template loaded");
    },

    onFailed: function(status, statusText) {
        console.log("Template failed: {status} {statusText}".substitute({
            status: status,
            statusText: statusText
        }));
    }
});

Sahris.UI = new Class({
    Extends: Component,

    templates: {
        error: "<h1>Error</h1><p class=\"message\">{message}</p>",
        meta: "<p>Last edited by {author} (Revision: {rev}) " +
            "about {date}</p>"
    },

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
        this.history = HistoryManager.register(this.historyKey, [1],
            function(values) {
                console.log("History: onMatch");
                console.log(values);
                if ($defined(this.page)) {
                    if (values && values[0]) {
                        this.displayPage(values[0]);
                    } else {
                        this.displayPage("FrontPage");
                    }
                }
            }.bind(this),
            function(values) {
                console.log("History: onGenerate");
                console.log(values);
                return [this.historyKey, "(", values[0], ")"].join("");

            }.bind(this),
            "(.*)");
        HistoryManager.start();

        this.menu = null;
    },

    _onButtonClicked: function(e) {
        console.log("Button Cliekd");
        console.log(e);
    },

    _onKeyPressed: function(e) {
        console.log("Key Pressed");
        console.log(e);
    },

    _onLinkClicked: function(e) {
        var hash = e.target.href;
        if (hash && hash[0] == "#") {
            hash = hash.replace(/^.*#/, "");
            this.history.setValue(0, hash);
            return false;
        }
    },

    _onTplLoaded: function() {
        this.el.getElements("#metanav a").on("click",
            this._onLinkClicked.bind(this));

        this.el.getElements("#ctxnav a").on("click",
            this._onLinkClicked.bind(this));

        $$("#editor textarea").set("width", this.el.getWidth());
        $$("#editor textarea").set("height", this.el.getHeight() * 0.8);

        var jsonRequest = new Request.JSON({
            url: "/getip",
            onSuccess: function(responseJSON, responseText) {
                var o = responseJSON;
                $$("#editor #fields input[name=author]").set("text", o);
            }.bind(this),
        });
        jsonRequest.get();

        var buttonCallback = function(e) {
            e.preventDefault();
            this.onButton(e);
        };
        $$("#buttons a").on("click", this._onButtonClicked.bind(this))

        $$("#content").on("dblclick", function() {
            this.edit(true);
        }.bind(this));

        $(document).on("keypress", this._onKeyPressed.bind(this));

        var pageEl = this.el.getElement("#content > #page");
        this.page = new Sahris.Page(pageEl, "/wiki", "FrontPage");
        this.page.on("loaded", this._onPageLoaded.bind(this));
        this.page.on("failed", this._onPageFailed.bind(this));
        this.page.on("linkClicked", this._onLinkClicked.bind(this));
        this.fire("loaded");
    },

    _onTplFailed: function(status, statusText) {
        this.fire("failed", [status, statusText]);
    },

    _onPageLoaded: function() {
        this.page.render();
        this.setTitle(this.page.name || this.page.title);
        if (this.page.name) {
            this.menu.setActive(this.page.name);
        }
        if (this.page.name) {
            this.el.getElement("#ctxnav a#history").set("href",
                "#History/" + this.page.name);
        }
    },

    _onPageFailed: function(status, statusText) {
        if (($type(status) == "boolean") && !(status)) {
            console.log(status);
            console.log(statusText);
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

    load: function() {
        this.tpl.load();
    },

    /* FIXME: Port to mootools
    edit: function(flag) {
        if (flag) {
            if (this.editing) return;
            this.viewing = false;
            this.editing = true;

            $("#page").hide();
            $("#editor").show();

            $("#editor #fields input[name=comment]").val("");

            $("#title").html("Editing: " + this.page.name);
            $("#editor textarea").val(this.page.text);

            $("#buttons a#a").text("Save");
            $("#buttons a#b").text("Cancel");
        } else {
            if (this.viewing) return;
            this.viewing = true;
            this.editing = false;
            $("#page").show();
            $("#editor").hide();
            $("#buttons a#a").text("Edit");
            $("#buttons a#b").text("More...");

            this.displayPage(this.page.name);
        }
    },

    save: function() {
        if (this.viewing) return;

        var data = {
            name: this.page.name,
            text: $("#editor #text textarea").val(),
            comment: $("#editor #fields input[name=comment]").val(),
            author: $("#editor #fields input[name=author]").val()
        };


        var callback = function(o) {
            this.setStatus(o.message);
            if (this.page.name == "SiteMenu") {
                this.menu.load();
            }
        };

        $.ajax({
            type: "POST",
            url: "/wiki/" + this.page.name,
            data: $.json.encode(data),
            dataType: "json",
            contentType: "application/javascript",
            success: callback.createDelegate(this)
        });

        this.edit(false);
    },
    */

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
        this.el.getElement("status").html(message);
    },

    setTitle: function(title) {
        $("title").set("text", title);
    },

    displayPage: function(name) {
        if (!$defined(name)) {
            name = "FrontPage";
        }
        this.page.load(name);
    },

    onLoaded: function() {
        console.log("UI loaded");
        if (this.menu == null) {
            this.menu = new Sahris.Menu($("menu"), "SiteMenu");
        }
        this.menu.load();
        this.displayPage();
    },

    onFailed: function(status, statusText) {
        console.log("UI failed: {status} {statusText}".substitute({
            status: status,
            statusText: statusText
        }));
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
            "failed": this.onFailed.bind(this)
        });

        this.parser = new Sahris.Parser();

        this.clear();
    },

    _onLinkClicked: function(e) {
        this.fire("linkClicked", e);
    },

    clear: function() {
        this.el.empty()
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
                    this.fire("failed", [o.success, o.message]);
                }
            }.bind(this),
            "onFailure": function(xhr) {
                this.fire("failed", [xhr.status, xhr.statusText]);
            }.bind(this)
        });
        jsonRequest.get();
    },

    render: function() {
        this.parser.parse(this.el, this.text);
    },

    onLoaded: function() {
        console.log("Page loaded:" + this.name);
        this.el.getElements("a").on("click", this._onLinkClicked.bind(this));
    },

    onFailed: function(status, statusText) {
        console.log("Page failed: {status} {statusText}".substitute({
            status: status,
            statusText: statusText
        }));
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
        this.page.on("failed", this._onPageFailed.bind(this));

        this.clear();
    },

    _onPageLoaded: function() {
        this.page.render();
        this.fire("loaded");
    },

    _onPageFailed: function(status, statusText) {
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
        this.el.getElements("li.active").removeClass("active");

        var el = this.el.getElement("li a[href=\"{name}\"".substitute(
            {name: name}));
        console.log(el);
        if ($defined(el)) {
            el.getParent().addClass("active");
        }
    },

    onLoaded: function() {
        console.log("Menu loaded");
    },

    onFailed: function(status, statusText) {
        console.log("Menu failed: {status} {statusText}".substitute({
            status: status,
            statusText: statusText
        }));
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

$(document).on("domready", function() {
    console.log("Ready!");
    new Sahris.App().run();
});
