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

    _onLinkClicked: function(e) {
        var hash = e.target.href;
        if (hash && hash[0] == "#") {
            hash = hash.replace(/^.*#/, "");
            this.history.setValue(0, hash);
            return false;
        }
    },

    _onTplLoaded: function() {
        this.fire("loaded");
    },

    _onTplFailed: function(status, statusText) {
        this.fire("failed", status, statusText);
    },

    load: function() {
        this.tpl.load();
    },

    onLoaded: function() {
        console.log("UI loaded");
        if (this.menu == null) {
            this.menu = new Sahris.Menu($("menu"), "SiteMenu");
        }
        this.menu.load();
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
        console.log("Page loaded");
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
        this.el.getElement("li.active").removeClass("active");
        this.el.getElement("li a[href=\"{name}\"".substitute(
            {name: name})).addClass("active");
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

/*
Sahris.Menu = function() {

    return {
        init: function() {
            this.addEvents(
                "loaded",
                "failed"
            );

            if (this.el == null) {
                this.el = $("#menu");
            }
            this.loaded = false;
    
            this.page = new Sahris.Page("SiteMenu");
            this.parser = new Sahris.Parser();
    
            this.page.on("loaded", this.onMenuLoaded, this);
            this.page.on("failed", this.onMenuFailed, this);
        },
    
        load: function() {
            this.page.load("SiteMenu");
        },

        onMenuLoaded: function(page) {
            var menu = $("#menu");
            menu.empty();

            this.parser.parse(menu[0], page.text);

            $("#menu a").click(function(e) {
                $("#menu li.first").removeClass("first active");
                $(this).parent().addClass("first active");
                var hash = this.href;
                if (hash && hash[0] == "#") {
                    hash = hash.replace(/^.*#/, '');
                    $.history.load(hash);
                    return false;
                }
            });
    
            $("#menu li:first").addClass("first active");
        },

        onMenuFailed: function(page) {
        }
    }
}

Sahris.UI = function() {
    var tpl    = null;
    var menu   = new Sahris.Menu();
    var page   = new Sahris.Page();
    var parser = new Sahris.Parser();

    var editing = false;
    var viewing = false;

    var templates = {
        error: $.template("<h1>Error</h1><p class=\"message\">${message}</p>"),
        meta: $.template("<p>Last edited by ${author} (Revision: ${rev}) " +
            "about ${date}</p>")
    };

    return {
        init: function() {
            this.addEvents(
                "loaded",
                "failed"
            );

            this.on("loaded", this.onLoaded, this);
            this.on("failed", this.onFailed, this);
            this.page.on("loaded", this.onPageLoaded, this);
            this.page.on("failed", this.onPageFailed, this);

            this.el = $("body");

            this.loaded = false;
            this.tpl = new Sahris.Template({
                url: "/templates/base.xhtml"
            });
        },
    
        load: function() {
            tpl.load();
            this.tpl.on("loaded", function(tpl) {
                this.fireEvent("loaded", tpl);
            }, this);
            this.tpl.on("failed", function(tpl) {
                this.fireEvent("failed", tpl);
            }, this);
        },

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

        displayPage: function(name) {
            this.page.load(name);
            this.pageEl.empty();
        },

        clearError: function() {
            if ($("#content").attr("class") == "error") {
                $("#content").switchClass("error", "content");
                $("#page").addClass("wiki");
            }
        },

        setError: function(message) {
            if ($("#content").attr("class") == "content") {
                $("#content").switchClass("content", "error");
            }
            this.pageEl.append(this.templates.error, {message: message});
        },

        setStatus: function() {
            var args = arguments;
            $("#status").fadeOut("slow", function() {
                if (args.length == 2) {
                    $("#status").empty().append(args[0], args[1]).fadeIn("slow");
                } else {
                    $("#status").empty().append(args[0]).fadeIn("slow");
                }
            });
        },

        setTitle: function(title) {
            $("#title").html(title);
        },

        onKeyPressed: function(e) {
            if (e.keyCode == 27) {
                if (this.editing) {
                    this.edit(false);
                }
            }
        },

        onButton: function(e) {
            var action = $(e.target).text();
            if (action == "Save") {
                this.save();
            } else if (action == "Cancel") {
                this.edit(false);
            } else if (action == "Edit") {
                this.edit(true);
            }
        },

        onHistory: function(hash) {
            var name = "";
            if (hash) {
                name = hash;
            } else {
                name = "FrontPage";
            }
            this.displayPage(name);
        },

        onLoaded: function(tpl) {
            this.el.html(tpl.text);

            this.pageEl = $("#content > #page");

            this.menu.load();

            $("#editor textarea").markItUp(mySettings);
            $("#editor textarea").width($("#content").width());
            $("#editor textarea").height($("#content").height() * 0.8);

            $.ajax({
                type: "GET",
                url: "/getip",
                dataType: "json",
                success: function(data) {
                    $("#editor #fields input[name=author]").val(data);
                }
            });

            $("#metanav a").click(function(e) {
                $("#menu li.first").removeClass("first active");
                var hash = this.href;
                if (hash && hash[0] == "#") {
                    hash = hash.replace(/^.*#/, '');
                    $.history.load(hash);
                    return false;
                }
            });

            $("#ctxnav a").click(function(e) {
                $("#menu li.first").removeClass("first active");
                var hash = this.href;
                if (hash && hash[0] == "#") {
                    hash = hash.replace(/^.*#/, '');
                    $.history.load(hash);
                    return false;
                }
            });

            var buttonCallback = function(e) {
                e.preventDefault();
                this.onButton(e);
            };
            $("#buttons a").click(buttonCallback.createDelegate(this));

            var dblclickCallback = function() {
                this.edit(true);
            };
            $("#content").dblclick(dblclickCallback.createDelegate(this));

            var keypressCallback = function(e) {
                this.onKeyPressed(e)
            };
            $(document).keypress(keypressCallback.createDelegate(this));

            var callback = function(hash) {
                this.onHistory(hash);
            };
            $.history.init(callback.createDelegate(this));
        },

        onFailed: function() {
        },

        onPageLoaded: function(page) {
            this.parser.parse(this.pageEl[0], page.text);

            $("#content > #page a").click(function(e) {
                $("#menu li.first").removeClass("first active");
                var hash = this.href;
                if (hash && hash[0] == "#") {
                    hash = hash.replace(/^.*#/, '');
                    $.history.load(hash);
                    return false;
                }
            });

            if (page.name) {
                $("#ctxnav a#history").attr("href", "#History/" + page.name);
            }

            this.setTitle(page.name || page.title);

            this.setStatus(this.templates.meta, {
                    author: page.author,
                    rev: page.rev,
                    date: prettyDate(page.date * 1000)
            });

            this.viewing = true;
        },

        onPageFailed: function(page) {
            this.setError(page.message);
        }
    }
}
*/

$(document).on("domready", function() {
    console.log("Ready!");
    new Sahris.App().run();
});
