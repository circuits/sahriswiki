/*
 * main
 *
 * @author      James Mills, prologic at shortcircuit dot net dot au
 * @copyright   (C) 2009, SoftCircuit (James Mills)
 * @date        8th July 2009
 *
 * @license     MIT (See LICENSE file in source distribution)
 */
 
//
// Main Entry Point
//

var creole = new Parse.Simple.Creole({
    interwiki: {
        MeatBall: "http://www.usemod.com/cgi-bin/mb.pl?"
    },
    linkFormat: "#",
    plugin: plugin
});

$.fn.switchClass = function(remove, add) {
    return $(this).removeClass(remove).addClass(add);
}

MODES = {
    view: 0,
    edit: 1
}

TEMPLATES = {
    NotFound: $.template("<h1>Error</h1><p class=\"message\">Page ${pagename} not found</p>"),
    PageMeta: $.template("<p>Last edited by ${author} (Revision: ${rev}) about ${date}</p>")
}

var mode = MODES.view;
var pagename = null;

function plugin(node, r, options) {
    eval(r[1] + "(node);");
}

function HelloWorld(node) {
    $(node).html("Hello World!");
}

function loadPage(name) {
    if (mode != MODES.view) return;
    pagename = name;
    $.getJSON("/wiki/" + name, function(data) {
        if ($("#content").attr("class") == "error") {
            $("#content").switchClass("error", "content");
            $("#page").addClass("wiki");
        }

        $("#title #backlink").text(name);
        $("#title #backlink").attr("href", "#BackLinks?name=" + name);

        var page = $("#content > #page");
        page.empty();

        if (data.success) {
            creole.parse(page[0], data.data.text);

            $("#content > #page a").click(function(e) {
                $("#menu li.first").removeClass("first active");
                var hash = this.href;
                if (hash && hash[0] == "#") {
                    hash = hash.replace(/^.*#/, '');
                    $.history.load(hash);
                    return false;
                }
            });

            historyPage = "#History/" + name;
            $("#ctxnav a#history").attr("href", historyPage);

            $("#status").empty().append(TEMPLATES.PageMeta, {
                    author: data.data.author,
                    rev: data.data.rev,
                    date: prettyDate(data.date * 1000)});
        } else {
            $("#content").switchClass("content", "error");
            page.removeClass("wiki");
            page.append(TEMPLATES.NotFound, {pagename: name});
        }
    });
}

function loadMenu() {
    $.getJSON("/wiki/SiteMenu", function(data) {
        var menu = $("#menu");
        menu.empty();
        creole.parse(menu[0], data.data.text);
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
    });
}

function doEdit() {
    if (mode != MODES.view) return;
    mode = MODES.edit;
    $("#page").hide();
    $("#editor").show();

    $("#editor #fields input[name=comment]").val("");

    $.getJSON("/wiki/" + pagename, function(data) {
        $("#title").html("Editing: " + pagename);
        $("#editor #text").val("");
        if (data.success) {
            $("#editor #text").val(data.data.text);
        } else {
            console.log("Error while trying to edit: " + pagename);
            console.log(data)
        }
    });

    $("#buttons a#a").text("Save");
    $("#buttons a#b").text("Cancel");
}

function doSave() {
    if (mode != MODES.edit) return;

    var data = {
        name: pagename,
        text: $("#editor #text").val(),
        comment: $("#editor #fields input[name=comment]").val(),
        author: $("#editor #fields input[name=author]").val()
    };

    $.ajax({
        type: "POST",
        url: "/wiki/" + pagename,
        data: $.json.encode(data),
        dataType: "json",
        contentType: "application/javascript",
        success: function(data) {
            console.log(data);
        }
    });

    doCancel();
}

function doCancel() {
    if (mode != MODES.edit) return;
    mode = MODES.view;
    $("#page").show();
    $("#editor").hide();
    $("#buttons a#a").text("Edit");
    $("#buttons a#b").text("More...");
    loadPage(pagename);
}

function history(hash) {
    if (hash) {
        pagename = hash;
    } else {
        pagename = "FrontPage";
    }
    loadPage(pagename);
}

function handleKeyPressed(e) {
    if (e.keyCode == 27) {
        if (mode == MODES.edit) {
            doCancel();
        }
    }
}

function main() {
    $.history.init(history);

    loadMenu();

    $("#editor #text").markItUp(mySettings);
    $("#editor #text").width($("#content").width());
    $("#editor #text").height($("#content").height() * 0.8);

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

    $("#buttons a").click(function(e) {
        e.preventDefault();
        var action = $(this).text();
        if (action == "Save") {
            doSave();
        } else if (action == "Cancel") {
            doCancel();
        } else if (action == "Edit") {
            doEdit();
        } else {
            console.log("Invalid action: " + action);
        }
    });

    $("#content").dblclick(doEdit);

    $(document).keypress(handleKeyPressed);
}
