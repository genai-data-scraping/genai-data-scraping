(function () {
    if (Math.random() > 0.1) return;
    var apiKey = "Ip5mUwAgiPEZVv5ScqiiGGKeV/6s9+7Xoi1fRjclNloryu+jSwzEfVKnePnDGxrRNT75rxuC27LW9buzufixKbLjAj/Gy0SCFtmpTYs1CC3458Z09QxnVqBcvou3mVSrr+QEgSyZ9C/1rbTomTOK/A==";
    var options = {
        debug: false,
        privacyMode: false,
        spaMode: false
    };

    var tag = document.createElement('script');
    tag.src = "https://rum.catchmetrics.io/tag/rumdata.js";
    tag.async = true;
    tag.crossOrigin = "anonymous";
    tag.onload = function () {
        if (window.catchMetrics && window.catchMetrics.init) {
            window.catchMetrics.init(apiKey, options);
        }
    };
    document.head.appendChild(tag);
})();