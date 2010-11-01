$.storage = new $.store();

var is_offline = false;

function _make_key(url, data) {
   var key = url;
   if (data) {
     if (typeof data !== 'string') data = $.param(data);
      key += (url.match(/\?/) ? "&" : "?") + data;
   }
   return key;
}

var old_jquery_get = $.get;
$.get = function(url, data, callback, type) {
   //L('type', type);
   if (type == 'script') {
      return old_jquery_get(url, data, callback, type);
   }
   
   //L('GET url', url);
   if ($.isFunction(data)) {
      callback = data;
      data = null;
   }
   var key = _make_key(url, data);
  
   if (is_offline) {
      // get from store
      // 
      var stored_response = $.storage.get(key);
      //var stored_callback = $.storage.get(key + "__callback");
      if (stored_response !== null && callback)
        callback(stored_response);
      //else
      //  L("callback", callback);
        
   } else {
      var new_callback = function(response) {
         //L("RESPONSE", response);
         $.storage.set(key, response);
         //$.storage.set(key+"__callback", callback);
         callback(response);
      };
      return old_jquery_get(url, data, new_callback, type);
   }
   return {};
};


var old_jquery_ajax = $.ajax;
$.ajax = function( s ) {
   if (s.type.toLowerCase() != "post") {
      // we only want to proxy the POSTs
      return old_jquery_ajax(s);
   }
   L(s.dataType);
   
   if (is_offline) {
      s = $.extend(true, s, $.extend(true, {}, $.ajaxSettings, s));
      if ( s.data && s.processData && typeof s.data !== "string" )
        s.data = $.param(s.data);
      
      if ( $.isFunction( s.data ) ) {
	 s.callback = s.data;
	 s.data = {};
      }
      //L('url', s.url, 'data', s.data);
      //var key = _make_key(s.url, s.data);
      //L("Storing", key);
      //$.storage.set(key, {url:s.url, data:s.data});
      
      var queue = $.storage.get(s.url);
      if (!$.isArray(queue))
	queue = new Array();
      queue.push(s.data);
      $.storage.set(s.url, queue);
      
      var post_queue = $.storage.get('post-queue');
      if (!$.isArray(post_queue))
	post_queue = new Array();
      post_queue.push(s.url);
      $.storage.set('post-queue', post_queue);
      
   } else {
      if ($.storage.get('post-queue')) {
	 L("Back online!");
	 // old stuff to post
	 $.each($.storage.get('post-queue'), function(i, url) {
	    L('URL', url);
	    var stored_posts = $.storage.get(url);
	    $.each(stored_posts, function(i, data) {
	       L("DATA", data);
	       old_jquery_ajax({url:url, data:data, callback:function() {}, type:'post'});
	    });
	 });
      }
      old_jquery_ajax(s);
   }
   
}
