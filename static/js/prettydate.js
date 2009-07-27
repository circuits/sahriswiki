/*
 * mootools Date extension for display pretty dates.
 *
 * CopyRight (C) 2009 James Mills
 * Based on John Resig's jquery.prettydate.js
 *
 * Licensed under the MIT license.
 */

Date.implement({
    pretty: function() {
        var diff = (((new Date()).getTime() - this.getTime()) / 1000);
        var day_diff = Math.floor(diff / 86400);
			
    	if (isNaN(day_diff) || day_diff < 0 || day_diff >= 31)
    		return;
			
    	return day_diff == 0 && (
    			diff < 60 && "just now" ||
    			diff < 120 && "1 minute ago" ||
    			diff < 3600 && Math.floor( diff / 60 ) + " minutes ago" ||
    			diff < 7200 && "1 hour ago" ||
    			diff < 86400 && Math.floor( diff / 3600 ) + " hours ago") ||
    		day_diff == 1 && "Yesterday" ||
    		day_diff < 7 && day_diff + " days ago" ||
    		day_diff < 31 && Math.ceil( day_diff / 7 ) + " weeks ago";
    }
});
