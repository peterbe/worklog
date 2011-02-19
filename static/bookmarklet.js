(function() {
    // Reference on use of outermost function() call and other JS modular design issues:
    // http://www.adequatelygood.com/2010/3/JavaScript-Module-Pattern-In-Depth
    
    var gc_base_url = "http://donecal.com/";
    //var gc_base_url = "http://worklog/";
   
    // Get first 3 characters of path
    var conversationPath = location.pathname.substring(0,3);
    
    // Current host:port
    var thisHost = location.host; // Ex: www.social.com:3000
    
    // Reg expression that will handle possible presence of leading "http://"
    // and trailing "/"  Almost identical to that in begin()
    var matchUrl = /((\w+\.)*((\w+)\.\w+))(:\d+)?(\/)?/;
    
    var resultBaseMatch = gc_base_url.match(matchUrl);
    var resultLocMatch = thisHost.match(matchUrl);
   

    // Geometry.js came from:
    // http://www.davidflanagan.com/javascript5/
    // Specifically Example 14-2
    // http://www.davidflanagan.com/javascript5/display.php?n=14-2&f=14/Geometry.js
    //
    // FYI - I bought the book.

    /**
     * Geometry.js: portable functions for querying window and document geometry
     *
     * This module defines functions for querying window and document geometry.
     * 
     * getWindowX/Y(): return the position of the window on the screen
     * getViewportWidth/Height(): return the size of the browser viewport area
     * getDocumentWidth/Height(): return the size of the document.
     * getHorizontalScroll(): return the position of the horizontal scrollbar
     * getVerticalScroll(): return the position of the vertical scrollbar
     *
     * Note that there is no portable way to query the overall size of the 
     * browser window, so there are no getWindowWidth/Height() functions.
     * 
     * IMPORTANT: This module must be included in the <body> of a document
     *            instead of the <head> of the document.
     */
    var Geometry = {};

    if (window.screenLeft) { // IE and others
        Geometry.getWindowX = function() { return window.screenLeft; };
        Geometry.getWindowY = function() { return window.screenTop; };
    }
    else if (window.screenX) { // Firefox and others
        Geometry.getWindowX = function() { return window.screenX; };
        Geometry.getWindowY = function() { return window.screenY; };
    }

    if (window.innerWidth) { // All browsers but IE
        Geometry.getViewportWidth = function() { return window.innerWidth; };
        Geometry.getViewportHeight = function() { return window.innerHeight; };
        Geometry.getHorizontalScroll = function() { return window.pageXOffset; };
        Geometry.getVerticalScroll = function() { return window.pageYOffset; };
    }
    else if (document.documentElement && document.documentElement.clientWidth) {
        // These functions are for IE6 when there is a DOCTYPE
        Geometry.getViewportWidth =
            function() { return document.documentElement.clientWidth; };
        Geometry.getViewportHeight = 
            function() { return document.documentElement.clientHeight; };
        Geometry.getHorizontalScroll = 
            function() { return document.documentElement.scrollLeft; };
        Geometry.getVerticalScroll = 
            function() { return document.documentElement.scrollTop; };
    }
    else if (document.body.clientWidth) {
        // These are for IE4, IE5, and IE6 without a DOCTYPE
        Geometry.getViewportWidth =
            function() { return document.body.clientWidth; };
        Geometry.getViewportHeight =
            function() { return document.body.clientHeight; };
        Geometry.getHorizontalScroll =
            function() { return document.body.scrollLeft; };
        Geometry.getVerticalScroll = 
            function() { return document.body.scrollTop; };
    }

    // These functions return the size of the document.  They are not window 
    // related, but they are useful to have here anyway.
    if (document.documentElement && document.documentElement.scrollWidth) {
        Geometry.getDocumentWidth =
            function() { return document.documentElement.scrollWidth; };
        Geometry.getDocumentHeight =
            function() { return document.documentElement.scrollHeight; };
    }
    else if (document.body.scrollWidth) {
        Geometry.getDocumentWidth =
            function() { return document.body.scrollWidth; };
        Geometry.getDocumentHeight =
            function() { return document.body.scrollHeight; };
    }

    // End Geometry.js

    // My additions to Geometry object

    if (window.innerWidth) { // All browsers but IE
        Geometry.setScrollPos = function(pos) { window.scrollTo(pos.x, pos.y) };
    }

    else if (document.documentElement && document.documentElement.clientWidth) {
        // These functions are for IE6 when there is a DOCTYPE
        Geometry.setScrollPos = function(pos) { document.documentElement.scrollLeft=pos.x; document.documentElement.scrollTop=pos.y };
    }
    else if (document.body.clientWidth) {
        // These are for IE4, IE5, and IE6 without a DOCTYPE
        Geometry.setScrollPos = function(pos) { document.body.scrollLeft=pos.x; document.body.scrollTop=pos.y };
    }



    // How many pixels shadow extends beyond canvas
    var kShadowSize = 10;

    // Dimensions of canvas.
    // These should be equal to the enclosed iframe document dimensions plus padding x 2.
    // See #custom-doc in enclosed iframe document for width - bookmarklet.css
    // See also clearspring_widget_window() and commonHead.html (linkback).
    var gCanvasWidthFull = 620;
    var gCanvasWidthMin = 140;
    var gCanvasWidth = gCanvasWidthFull;
    
    var gCanvasHeightFull = 400;
    var gCanvasHeightHalf = 175;
    var gCanvasHeightMin = 45;
    var gCanvasHeight = gCanvasHeightFull;

    // Record current location.href
    var g_locationHref = location.href;

    // Current scroll position
    var gCurScroll = scrollPos();


    // An array of embeds and their current style.visibility values;
    //
    var gEmbedArr; // Initialized by call to getElementsByTagName()
    var gEmbedVisibilityArr = new Array();

    function bookmarklet() {
        // Does frame already exist?  If so, return.
        if (byId("bigt__container")) {
            return;
        }

        // Capture any highlighted text
        var highlightedText = "";

        // Firefox, Safari, Google Chrome
        if (window.getSelection) {
            highlightedText = '' + window.getSelection();
        } 
        
        // Internet Explorer
        else if (document.selection) {
            highlightedText = document.selection.createRange().text;
        }

        // Capture no more than 350 characters.
        // This should be at least as great as largest max_tweetCharCount
        // for any Service.  See also commonStatic.js, gc_tweetCookieSize
        //
        // Max URL size should also be considered (2083 chars for IE).
        highlightedText = highlightedText.substr(0,350);


        // Get array of embeds, store current value of style.visibility,
        // and then set to "hidden" for the duration of our bookmarklet.
        gEmbedArr = document.getElementsByTagName('embed');
        for(var i=0; i<gEmbedArr.length; i++){
            gEmbedVisibilityArr[i] = gEmbedArr[i].style.visibility;
            gEmbedArr[i].style.visibility='hidden';
        }


        // Create the BigTweet frame
        var container = div();
        container.id = "bigt__container";
        container.style.position = "absolute";
        //container.style.top = scrollPos().y + (Geometry.getViewportHeight() - gCanvasHeightFull)  + "px";
       container.style.top = scrollPos().y + 50  + "px";
        container.style.right = (Geometry.getViewportWidth() - gCanvasWidth)/2 + "px";
        container.style.zIndex = 100000;

        // Give the container width and height that will override any
        // setting for div from parent stylesheet.
        container.style.width = gCanvasWidth + kShadowSize + "px";
        container.style.height = gCanvasHeight + kShadowSize + "px";

        //var shadow = div(container);
        //shadow.id = "bigt__shadow";
        //shadow.style.backgroundColor = "black";
        //shadow.style.position = "absolute";
        //shadow.style.zIndex = 0;
        //shadow.style.top = "0";
        //shadow.style.right = "0";
        //setOpacity(shadow, 0.3);

        var canvas = div(container);
        canvas.id = "bigt__canvas";
        //canvas.style.backgroundColor = "white";
        canvas.style.zIndex = 2;
        canvas.style.width = gCanvasWidth + "px"; 
        canvas.style.height = gCanvasHeight + "px";
        canvas.innerHTML = '<iframe scrolling="no" frameborder="0" id="bigt__iframe" style="width:100%;height:100%;border:0px;padding:0px;margin:0px;visibility:visible"></iframe>';

        canvas.style.position = "absolute";

        // Center the canvas within the shadow
        canvas.style.top = kShadowSize/2 + "px";
        canvas.style.right = kShadowSize/2 + "px";
    
        // Logo initially invisible
	/*
        var img_logo = document.createElement('img');
        img_logo.id = "bigt__logo";
        img_logo.src = gc_base_url + "static/images/logo/social_logo_39x39.png";
        img_logo.width = 39;
        img_logo.height = 39;
        img_logo.title = "Use controls on right to adjust window size or close";
        img_logo.style.position = "absolute";
        img_logo.style.visibility = "hidden";
        img_logo.style.zIndex = 3;
        img_logo.style.top = kShadowSize/2 + "px";;
        img_logo.style.right = kShadowSize/2 + 8 + (18 + 4) * 4 + "px";;
        container.appendChild(img_logo);   
	 */
       
        // Insert window controls (min, half, full, close)
        //insertSizeDiv("bigt__minWinDiv","bigt__minWinImg",minWin, "Minimize bookmarklet window",3,"min_win.png",5);
        //insertSizeDiv("bigt__halfWinDiv","bigt__halfWinImg",halfWin, "Half size bookmarklet window",2,"half_win.png",9);
        //insertSizeDiv("bigt__fullWinDiv","bigt__fullWinImg",windowActive, "Full size bookmarklet window",1,"full_win_selected.png",18);
        
       var closer= insertSizeDiv("bigt__closeWinDiv","bigt__closeWinImg",closeFrame, "Close bookmarklet window",0,"static/css/ext/fancybox/fancy_close.png",18);
       closer.style.top = "45px";
       closer.style.right = "10px";
        
        document.body.appendChild(container);



        // Note: Parameters encoded with encodeURIComponent() are automatically
        //       decoded by Catalyst when fetching $c->request->param('n_foobar')
        var docTitle = document.title;

        // Strip spaces at start and end of title and newlines everywhere
        // A site where I ran across the need for this was dictionary.com
        docTitle = docTitle.replace(/^\s+/,"");
        docTitle = docTitle.replace(/\s+$/,"");
        docTitle = docTitle.replace(/\n+/,"");

        // Capture no more than 280 characters
        docTitle = docTitle.substr(0,280);


        // Encode document title, location and highlighted text
        docTitle = encodeURIComponent(docTitle);
        var docLocation = encodeURIComponent(g_locationHref);
        highlightedText = encodeURIComponent(highlightedText);
        

        // Set the URL for the frame
        setFrameUrl(docTitle,docLocation,highlightedText);

        // Size the shadow as the DIV changes
        // Not clear exactly why we need to check this on an interval?
        var lastShadowWidth = 0;
        var lastShadowHeight = 0;
        function resizeShadow() {
            var shadow = byId("bigt__shadow");
            var canvas = byId("bigt__canvas");
            if (!shadow || !canvas) {
                clearInterval(interval);
                return;
            }
            if (lastShadowWidth != canvas.offsetWidth ||
                lastShadowHeight != canvas.offsetHeight) {
                lastShadowWidth = canvas.offsetWidth;
                lastShadowHeight = canvas.offsetHeight;
                shadow.style.width = (lastShadowWidth + kShadowSize) + "px";
                shadow.style.height = (lastShadowHeight + kShadowSize) + "px";
            }
        }
        var interval = window.setInterval(function() {
                checkForFrameMessage();
                resizeShadow();
            }, 50);
        resizeShadow();

        // Keep container in same relative position at top 
        // of visible window as user scrolls vertically.
        window.onscroll = function() {
            container.style.top = scrollPos().y + (Geometry.getViewportHeight() - gCanvasHeightFull)/2  + "px";
        };
        
        function insertSizeDiv(divId,imgId,func,titleMsg,order,imgSrc,imgHeight){
            var img_link_div;
            var img_link;
            
            img_link_div = div();
            img_link_div.id = divId;
            //img_link_div.onmouseover = highlightDiv;
            //img_link_div.onmouseout = unhighlightDiv;
            //img_link_div.style.backgroundColor = "#FFFFFF";
            img_link_div.onclick = func;
            img_link_div.style.width = "25px";
            img_link_div.style.height = "24px";
            img_link_div.style.border = "0px none";
            img_link_div.title = titleMsg;
            img_link_div.style.position = "absolute";
            img_link_div.style.zIndex = 3;
            img_link_div.style.top = kShadowSize/2 + 2 + "px";
            img_link_div.style.right = kShadowSize/2 + 2 + (24 + 4) * order + "px";
            container.appendChild(img_link_div); 
            
            img_link = document.createElement('img');
            img_link.id = imgId;
            img_link.src = gc_base_url + imgSrc;
            img_link.width = 25;
            img_link.height = 24;
            img_link.style.position = "absolute";
            img_link.style.zIndex = 3;
            img_link.style.top = "0px";
            img_link.style.right = "0px";
            img_link_div.appendChild(img_link);
           return img_link_div;
        }
    }
    
    function highlightDiv(e){
        this.style.border = "1px dotted black";
    }
    
    function unhighlightDiv(e){
        this.style.border = "0px none";
    }



    // See page 276 of my Javascript book for a better method
    // of getting measurements.
    function scrollPos() {
        return {
            x: Geometry.getHorizontalScroll(),
                y: Geometry.getVerticalScroll()
                };
    }


    function div(opt_parent) {
        var e = document.createElement("div");
        e.style.padding = "0";
        e.style.margin = "0";
        e.style.border = "0";
        e.style.position = "relative";
        if (opt_parent) {
            opt_parent.appendChild(e);
        }
        return e;
    }
    function byId(id) {
        return document.getElementById(id);
    }
    function setOpacity(element, opacity) {
        if (navigator.userAgent.indexOf("MSIE") != -1) {
            var normalized = Math.round(opacity * 100);
            element.style.filter = "alpha(opacity=" + normalized + ")";
        } else {
            element.style.opacity = opacity;
        }
    }

    // Check for frame messages from application
    function checkForFrameMessage() {
        var hash = location.href.split('#')[1]; 
        if ( !hash || ((hash != "bigtweet_close") && (hash != "bigtweet_minimize")) ) {
            gCurScroll = scrollPos(); // update copy of current scroll position
            return;
        }
        
        if(hash == "bigtweet_close"){
            closeFrame();
        }
        else if(hash == "bigtweet_minimize"){
            minWin();
        }

        // Restore original location.href (hash was altered by call in iframe)
        // Empty hash must be appended to restore page position.
        try {
            top.location.replace(g_locationHref.split("#")[0] + "#");
        } catch (e) {
            top.location = g_locationHref.split("#")[0] + "#";
        } 

        var pos = gCurScroll;
        Geometry.setScrollPos(pos);
        window.setTimeout(function() { Geometry.setScrollPos(pos); }, 10);
    }
    
    
   /*
    function fullWin(){
        gCanvasWidth = gCanvasWidthFull;
        gCanvasHeight = gCanvasHeightFull;
        
        var iframe = byId('bigt__iframe');
        iframe.style.visibility = "visible";
        
        var container = byId('bigt__container');
        container.style.width = gCanvasWidth + kShadowSize + "px";
        container.style.height = gCanvasHeight + kShadowSize + "px";
        
        var canvas = byId('bigt__canvas');
        canvas.style.width = gCanvasWidth + "px";
        canvas.style.height = gCanvasHeight + "px";
        
        //var img_logo = byId('bigt__logo');
        //var minWinDiv = byId('bigt__minWinDiv');
        //var minWinImg = byId('bigt__minWinImg');
        //var halfWinDiv = byId('bigt__halfWinDiv');
        //var halfWinImg = byId('bigt__halfWinImg');
        //var fullWinDiv = byId('bigt__fullWinDiv');
        //var fullWinImg = byId('bigt__fullWinImg');
        
        // Logo not visible
        //img_logo.style.visibility = "hidden";
        
        // Min Window is no longer active
        //minWinDiv.onclick = minWin;
        //minWinImg.src = gc_base_url + "static/images/bookmarklet/min_win.png";
        
        // Half Window is no longer active
        //halfWinDiv.onclick = halfWin;
        //halfWinImg.src = gc_base_url + "static/images/bookmarklet/half_win.png";
        
        // Full Window is now active
        //fullWinDiv.onclick = windowActive;
        //fullWinImg.src = gc_base_url + "static/images/bookmarklet/full_win_selected.png";
        
        // Reposition window to center
        //container.style.top = scrollPos().y + (Geometry.getViewportHeight() - gCanvasHeightFull)/2  + "px";
       container.style.top = scrollPos().y + 60  + "px";
        container.style.right = (Geometry.getViewportWidth() - gCanvasWidth)/2 + "px";
        
        // Keep container in same relative position at top 
        // of visible window as user scrolls vertically.
        window.onscroll = function() {
            container.style.top = scrollPos().y + (Geometry.getViewportHeight() - gCanvasHeightFull)/2  + "px";
        };
    }
    */

    // Do nothing for active window.
    function windowActive(){
          
    }

    function closeFrame(){
        var my_iframe = byId('bigt__iframe'); // Parent is canvas
        var canvas = byId('bigt__canvas'); // Parent is container
        //var shadow = byId('bigt__shadow'); // Parent is container
        var container = byId('bigt__container');
       var close_div = byId('bigt__closeWinDiv');
        
        // Remove container elements starting with lowest.
        //
        // Note:  It is not sufficient to just remove container.  This
        //        resulted in strange behaviour on IE8 (could not set
        //        focus on document elements after closing bookmarklet).
        //        To address IE8 bug, I needed to remove iframe and/or canvas.
        //
        my_iframe.parentNode.removeChild(my_iframe);
        canvas.parentNode.removeChild(canvas);
        close_div.parentNode.removeChild(close_div);
        //shadow.parentNode.removeChild(shadow);
        container.parentNode.removeChild(container);
        

        // Restore original onkeyup handler
        document.onkeyup = g_origKeyUp;

        // Restore visibility values for embeds
        try {
            for(var i=0; i<gEmbedArr.length; i++){
                gEmbedArr[i].style.visibility = gEmbedVisibilityArr[i];
            }
        } catch (e) {
            ;
        }

    }

    function setFrameUrl(docTitle,docLocation,highlightedText) {
        var iframe;
        if (navigator.userAgent.indexOf("Safari") != -1) {
            iframe = frames["bigt__iframe"];
        } else {
            iframe = byId("bigt__iframe").contentWindow;
        }
        if (!iframe) {
            return;
        }

        // Let's make sure that we don't have a null title
        if(docTitle == ''){
            docTitle = '-';
        }

        // Let's make sure that some glitch doesn't give us a null
        // docLocation
        if(docLocation == ''){
            docLocation = 'about:blank';
        }

        // Note:
        // The order here is strict and is depended on by clearspring_widget_inline(), Root.pm
        // for substitutions.
        var url = gc_base_url + 'bookmarklet/?external_url=' + docLocation + '&doc_title=' + docTitle;// + '&n_highlighted_text=' + highlightedText;

        try {
            iframe.location.replace(url); // Apparently works in Safari also
        } catch (e) {
            iframe.location = url; // Other browers?
        }
    }


    // New onkeyup handler
    function handleOnkeyup(e){
        var evtobj=window.event? event : e;
	var unicode=evtobj.charCode? evtobj.charCode : evtobj.keyCode;
       
        // Close bookmarklet on Escape
	if(unicode == 27){
            closeFrame();
	}
    }

    // Preserve original onkeyup handler
    var g_origKeyUp = document.onkeyup;
    
    // Substitute new onkeyup
    document.onkeyup = handleOnkeyup;

    bookmarklet();
   
})();
