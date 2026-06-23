window.iovoxDniApi = {
    setReferrer: function(){
        var channelData = iovoxApiConfig.referringDomains ? iovoxApiConfig.referringDomains :
                [
                    {"domain":"google","source":"organic"},
                    {"domain":"bing","source":"organic"},
                    {"domain":"yahoo","source":"organic"},
                    {"domain":"facebook","source":"social"},
                    {"domain":"linkedin","source":"social"},
                    {"domain":"twitter","source":"social"},
                    {"domain":"","source":"direct"},
                    {"domain":"no_match_default","source":"other"}
                ],
            referringDom = document.referrer,
            currentUrl = document.location.href,
            directReferrer = iovoxDniApi.getChannelDefaults(channelData, ''),
            defaultReferrer = iovoxDniApi.getChannelDefaults(channelData, 'no_match_default'),
            referringSource = false;

        if (!iovoxDniApi.getCookie("iovoxMCM")) {
            //check if referrer is a specified channel
            if (referringDom || iovoxApiConfig.uriMatching) {
                for (i = 0; i < channelData.length; i++) {
                    if (referringDom.indexOf(channelData[i].domain) > -1) {
                        referringSource = channelData[i].source;
                    }
                }
                // if current url matching is requested
                // check the channel data
                // note this will supersede referring dom
                if(iovoxApiConfig.uriMatching) {
                    for (i = 0; i < channelData.length; i++) {
                        if (currentUrl.indexOf(channelData[i].domain) > -1) {
                            referringSource = channelData[i].source;
                        }
                    }
                }
            } else {
                if (directReferrer) {
                    referringSource = directReferrer;
                }
            }

            //set referring channel to ppc if adwords is set
            if (!!iovoxDniApi.getCookie("iovoxAdWords")) {
                iovoxDniApi.setCookie("iovoxMCM", "PPC");
            } else {
                iovoxDniApi.setCookie("iovoxMCM", referringSource ? referringSource : defaultReferrer);
            }
        }
        return iovoxDniApi.getCookie("iovoxMCM");
    },
    getChannelDefaults: function(channelData, channelType){
        var thisChannelSource = false;
        //loop the channels and return the matched source
        for(i = 0; i < channelData.length; i++) {
            if(channelData[i].domain === channelType){
                thisChannelSource = channelData[i].source;
                //pop the index from the array and return it to the the request
                channelData.splice(i,1);
                return thisChannelSource;
            }
        }
        return thisChannelSource;
    },
    referrerCheck: function(linkId){
        var seoPattern = /organic\b/i,
            socialPattern = /social\b/i,
            otherPattern = /other\b/i,
            seoMatch = linkId.match(seoPattern),
            socialMatch = linkId.match(socialPattern),
            otherMatch = linkId.match(otherPattern);

        if(!seoMatch && !socialMatch && !otherMatch){
            if(iovoxDniApi.getCookie("iovoxMCM")){
                return iovoxApiConfig.replaceLinkId ? iovoxDniApi.getCookie("iovoxMCM") : linkId +"_"+ iovoxDniApi.getCookie("iovoxMCM");
            } else {
                return iovoxApiConfig.replaceLinkId ? iovoxApi.setReferrer() : linkId +"_"+ iovoxDniApi.setReferrer();
            }
        } else {
            if(!iovoxDniApi.getCookie("iovoxMCM")) {
                if (seoMatch) {
                    iovoxDniApi.setCookie("iovoxMCM", "organic");
                } else if (socialMatch) {
                    iovoxDniApi.setCookie("iovoxMCM", "social");
                } else {
                    iovoxDniApi.setCookie("iovoxMCM", "other");
                }
            }
            return linkId;
        }

    },
    create_UUID: function () {
        var dt = new Date().getTime();
        var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = (dt + Math.random()*16)%16 | 0;
            dt = Math.floor(dt/16);
            return (c=='x' ? r :(r&0x3|0x8)).toString(16);
        });
        return uuid;
    },
    initSessionKey: function () {
        var cookie = iovoxDniApi.getCookie('iovox_id');
        if(!cookie) {
            cookie = iovoxDniApi.create_UUID();
            iovoxDniApi.setCookie('iovox_id', cookie, null, iovoxApiConfig.forceDomainCookie);
        }
        return cookie;
    },

    perSourcePaidReferences: {
        adwords: 'gclid',
        bing: 'mscklid',
        facebook: 'fclid',
        adobe: 'dcid'
    },
    perSourceParse: function (key) {
        switch (key) {
            case '_referer':
                if(document.referrer == "") {
                    return "_direct_";
                } else {
                    var url = new URL(document.referrer);
                    return url.hostname;
                }
                break;
            case '_paid':
            case '_paidpersource':
                var url = new URL(window.location.href);
                var sources = [];
                for(var source in iovoxDniApi.perSourcePaidReferences) {
                    if(url.searchParams.get(iovoxDniApi.perSourcePaidReferences[source]) !== null) {
                        sources.push(source);
                    }
                }
                if(sources.length > 0) {
                    return key == '_paid' ? '_paid_' :  '_paid,' + sources.join(',') + '_';
                }
                break;
        }
        var url = new URL(window.location.href);
        if ((c = url.searchParams.get(key)) !== null) {
            return c;
        }
        return 'none';
    },
    initPerSourceKey: function (sources) {
        var cookie = iovoxDniApi.getCookie('iovox_source_id');
        if(!cookie) {
            sources.sort();
            cookie = [];
            if (typeof sources != 'object') {
                sources = [sources];
            }
            for(var i in sources) {
                if(typeof sources[i] == 'string') {
                    cookie.push(iovoxDniApi.perSourceParse(sources[i]));
                }
            }
            cookie = cookie.join('-');
            iovoxDniApi.setCookie('iovox_source_id', cookie, null, iovoxApiConfig.forceDomainCookie);
        }
        return cookie;
    },
    getSeaInformation: function () {
        var s = iovoxDniApi.getCookie('iovox_sea');
        if(s) {
            return JSON.parse(atob(s));
        }
        _sea = {};
        _sea['first_visit'] = new Date();
        _sea['referer_page'] = document.referrer;
        _sea['first_page'] = window.location.href;
        iovoxDniApi.setCookie('iovox_sea', btoa(JSON.stringify(_sea)), null, iovoxApiConfig.forceDomainCookie);
        return _sea;
    },
    getSessionInformation: function () {
        var info = {
            _ga: '',
            adobe: ''
        }
        if(iovoxDniApi.getCookie('_ga')){
            info['_ga'] = iovoxDniApi.getCookie('_ga').split('.').slice(2,4).join('.');
        }
        var cookies = iovoxDniApi.listCookies();
        for(var i in cookies) {
            if(cookies[i].match(/@Adobe.org/) || cookies[i].match(/@AdobeOrg/)) {
                var cookie = iovoxDniApi.getCookie(cookies[i]).split('|');
                cookie.shift();
                var values = {};
                var k = '';
                for(var i in cookie) {
                    if(k == '') {
                        k = cookie[i];
                    } else {
                        values[k] = cookie[i];
                        k = '';
                    }
                }
                info['adobe'] = values['MCMID'] || '';
            }
        }
        return info;
    },
    getParameterByName: function(name, url) {
        if (!url) url = window.location.href;
        name = name.replace(/[\[\]]/g, "\\$&");
        var regex = new RegExp("[?&]" + name + "(=([^&#]*)|&|#|$)"),
            results = regex.exec(url);
        if (!results) return null;
        if (!results[2]) return '';
        return decodeURIComponent(results[2].replace(/\+/g, " "));
    },
    processNumber: function(number){
        var mask = "";
        var length = 0;
        for(var i = 0; i < number.length; i++){
            if(!isNaN(parseInt(number[i]))){
                mask += 'x';
                length ++;
            } else if(number[i] !== '+'){
                mask += number[i];
            }
        }
        return {mask:mask,length:length};
    },
    numberFormat: function(mask, number, isLocalized) {
        isLocalized = isLocalized || false;
        var localized = false;
        var formattedNumber = '';
        switch (mask) {
            case 'x xxx xxx xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 $2 $3 $4');
                break;
            case 'x (xxx) xxx xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 ($2) $3 $4');
                break;
            case 'x (xxx) xxx-xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 ($2) $3-$4');
                break;
            case 'xxx xxx xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$2 $3 $4');
                break;
            case 'xxx xxx.xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$2 $3.$4');
                break;
            case 'xxx.xxx.xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$2.$3.$4');
                break;
            case '(xxx) xxx xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '($2) $3 $4');
                break;
            case '(xxx) xxx.xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '($2) $3.$4');
                break;
            case '(xxx).xxx.xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '($2).$3.$4');
                break;
            case 'xxx xxx-xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$2 $3-$4');
                break;
            case '(xxx) xxx-xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '($2) $3-$4');
                break;
            case 'xxx-xxx-xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$2-$3-$4');
                break;
            case '(xxx)-xxx-xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '($2)-$3-$4');
                break;
            case '(xxx)xxx-xxxx':
                formattedNumber = number.replace(/(\d{1})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '($2)$3-$4');
                break;
            case 'xx xxx xx xx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{3})[^\d]*(\d{2})[^\d]*(\d{2})/, '$1 $2 $3 $4');
                break;
            case 'xxx xx xx xx':
                prefix = '';
                if(number.match(/^338/)) {
                    localized = true;
                    number = number.substr(2);
                    prefix = '0 ';
                }
                formattedNumber = number.replace(/(\d{3})[^\d]*(\d{2})[^\d]*(\d{2})[^\d]*(\d{2})/, prefix + '$1 $2 $3 $4');
                break;
            case 'xxx xxx xxx':
                prefix = number.match(/^338/) ? '0' : '';
                formattedNumber = number.replace(/3[34](\d{3})[^\d]*(\d{3})[^\d]*(\d{3})/, prefix + '$1 $2 $3');
                localized = true
                break;
            case 'xxx xxx xxxxx':
                formattedNumber = number.replace(/(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 $2 $3');
                break;
            case 'xx xxx xxx xxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 $2 $3 $4');
                break;
            case 'xx (x)xxx xxx xxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 (0)$2 $3 $4');
                break;
            case 'xx [x]xxx xxx xxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{3})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 [0]$2 $3 $4');
                break;
            case 'xx (x)xx xxxx xxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{2})[^\d]*(\d{4})[^\d]*(\d{4})/, '$1 (0)$2 $3 $4');
                break;
            case 'xx [x]xx xxxx xxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{2})[^\d]*(\d{4})[^\d]*(\d{4})/, '$1 [0]$2 $3 $4');
                break;
            case 'xx (x)x xx xx xx xx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{1})[^\d]*(\d{2})[^\d]*(\d{2})[^\d]*(\d{2})[^\d]*(\d{2})/, '$1 (0)$2 $3 $4 $5 $6');
                break;
            case 'xx xx xxxxxxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{2})[^\d]*(\d{8})/ ,'$1 $2 $3');
                break;
            case 'xx (x)xxx xxxxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{3})[^\d]*(\d{6})/ ,'$1 (0)$2 $3');
                break;
            case 'xx xx xxx xxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{2})[^\d]*(\d{3})[^\d]*(\d{4})/, '$1 $2 $3 $4');
                break;
            case 'xxxxx xxxxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{4})[^\d]*(\d{6})/, '0$2 $3');
                localized = true
                break;
            case 'xxxxxxxxxx':
                formattedNumber = number.replace(/(\d{2})[^\d]*(\d{10})/, '0$2');
                localized = true
                break;

            case 'xx xx xx xx xx':
                formattedNumber = number.replace(/33(\d{1})[^\d]*(\d{2})[^\d]*(\d{2})[^\d]*(\d{2})[^\d]*(\d{2})/, '0$1 $2 $3 $4 $5');
                localized = true
                break;
            case 'x xxx xxx xxx':
                formattedNumber = number.replace(/33(\d{3})[^\d]*(\d{3})[^\d]*(\d{3})/, '0 $1 $2 $3');
                localized = true;
                break;
            case '0XX? XXXXXXXX':
                if(number.match(/^390[26]/)) {
                    formattedNumber = number.replace(/390(\d{1})(\d+)/, '0$1 $2');
                } else if (number.match(/^390.[0159]/) || number.match(/^393/)) {
                    formattedNumber = number.replace(/39(.\d{2})(\d+)/, '$1 $2');
                } else {
                    formattedNumber = number.replace(/390(\d{3})(\d+)/, '0$1 $2');
                }

                localized = true
                break;
            default:
                formattedNumber = number;
        }

        return isLocalized ? [formattedNumber, localized] : formattedNumber;
    },
    listCookies: function () {
        var decodedCookie = decodeURIComponent(document.cookie);
        var _cookies = decodedCookie.split(';');
        var cookies = [];
        for(var i in _cookies) {
            cookies.push(_cookies[i].split('=')[0]);
        }
        return cookies;
    },
    getCookie: function(name){
        var decodedCookie = decodeURIComponent(document.cookie);
        var pattern = RegExp(name + "=.[^;]*"),
            matched = decodedCookie.match(pattern),
            cookie;
        if(matched){
            cookie = matched[0].split('=');
            return cookie[1];
        }
        return false;
    },
    setCookie: function(name, value, expires, domain){
        //sets session cookie with passed attributes
        var exp = expires ? "expires="+ expires +";" : "";
        var dom = domain ? ("domain=" + domain + ";") : "";
        document.cookie = name +"="+ value +"; path=/;"+ exp + dom;
    },
    deleteCookie: function(name){
        document.cookie = name +"=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;";
    },
    eraseSession: function () {
        iovoxDniApi.deleteCookie('iovox_source_id');
        iovoxDniApi.deleteCookie('iovox_sea');
        iovoxDniApi.deleteCookie('iovox_id');
        window.localStorage.removeItem('iovox_sea');
    },
    setVoxNumbers: function(iovoxNumberData){
        var adWordsTarget,
            adWordsNumber = iovoxApiConfig.adWordsNumber ? iovoxApiConfig.adWordsNumber : false,
            refDomFallback = false,
            phonePrefix = '',
            adWordsTargetItem, thisLinkTarget, thisNumber,
            sessionCodeTarget, sessionCodeExp, thisNumberFormat,
            thisDialString;

        //copy the base request data to return data for updating
        iovoxApiData.returnData = iovoxApiData.requestData;

        //make sure we have data to work with
        if(iovoxNumberData.items.length) {
            //get the referring domain fall back number
            for (var h = 0; h < iovoxNumberData.items.length; h++) {
                if (iovoxNumberData.items[h].linkid === iovoxDniApi.getCookie('iovoxMCM')) {
                    refDomFallback = iovoxNumberData.items[h].phonenumber;
                }
            }
        }
        //add AdWordsTargets to voxReturnData
        if(iovoxApiConfig.adWordsTarget){
            adWordsTarget = iovoxApiConfig.adWordsTarget.split(',');
            for (var i = 0; i < adWordsTarget.length; i++) {
                adWordsTargetItem = {};
                adWordsTargetItem.linkId = 'adwords-location_'+adWordsTarget[i];
                adWordsTargetItem.selector = adWordsTarget[i];
                iovoxApiData.returnData.items.push(adWordsTargetItem);
            }
        }
        //process all the data
        if(iovoxApiData.returnData.items.length) {
            //loop the returned objects (cloned from request)
            for (var j = 0; j < iovoxApiData.returnData.items.length; j++) {
                //set the request target
                thisLinkTarget = iovoxApiData.returnData.items[j].selector ? document.querySelectorAll(iovoxApiData.returnData.items[j].selector) : false;
                //loop the api response for matches
                for (var k = 0; k < iovoxNumberData.items.length; k++) {
                    thisNumber = false;
                    //if we have a match update the returned data and the target object
                    if (iovoxNumberData.items[k].linkid.match(new RegExp(iovoxApiData.returnData.items[j].linkId, "i"))) {
                        if(adWordsNumber){
                            iovoxApiData.returnData.items[j].linkId = 'adwords-override';
                        }
                        //push the phone number to return data and set thisLinkNumber
                        iovoxApiData.returnData.items[j].phoneNumber = thisNumber = adWordsNumber ? adWordsNumber : iovoxNumberData.items[k].phonenumber;
                        thisNumberFormat = iovoxApiConfig.globalNumberFormat ? iovoxApiConfig.globalNumberFormat : iovoxApiData.returnData.items[j].numberFormat.mask;
                        thisDialString = iovoxApiData.returnData.items[j].oriDialString || iovoxApiData.returnData.items[j].dialString;
                        break;
                    }
                }
                //if no api match for the requested linkId
                if (!thisNumber) {
                    //check for adwords and fall back
                    if (adWordsNumber || refDomFallback) {
                        //push the phone number to return data and set thisLinkNumber
                        iovoxApiData.returnData.items[j].linkId = adWordsNumber ? 'adwords-override' : 'fallback-referrer';
                        iovoxApiData.returnData.items[j].phoneNumber = thisNumber = adWordsNumber ? adWordsNumber : refDomFallback;
                    }

                }
                //update the dom element(s) if they are not manually handling results
                if (!iovoxApiConfig.manualNumberUpdate) {
                    //push the update to the object
                    if (thisLinkTarget.length) {
                        //loop the link targets
                        for (var l = 0; l < thisLinkTarget.length; l++) {
                            if(thisNumber) {
                                //check for + in number display
                                var replaceInnerHTML = true;
                                var formattedNumberList = iovoxDniApi.numberFormat(thisNumberFormat, thisNumber, true);
                                var formattedNumber = formattedNumberList[0];
                                var isLocalized = formattedNumberList[1];
                                phonePrefix = '';
                                if (!isLocalized && thisLinkTarget[l].innerHTML.replace(/\w+/, '').slice(0, 1) === '+') {
                                    phonePrefix = '+';
                                }

                                //check if target is a anchor and update the href tel:
                                if (thisLinkTarget[l].nodeName == 'A') {
                                    //Check if ref has the + as it may be different between the visual number and the actual number to make the call.
                                    if(thisLinkTarget[l].href.substr(0, 5) == 'tel:+') {
                                        thisLinkTarget[l].href = 'tel:+' + thisNumber;
                                    } else if(thisLinkTarget[l].href.substr(0, 4) == 'tel:') {
                                        thisLinkTarget[l].href = 'tel:' + phonePrefix + iovoxDniApi.numberFormat(thisNumberFormat, thisNumber).replace(/\D+/g, '');
                                    }
                                    // first case, we do have <a><i img>XX XX XX</a>, second case, <a> doesn't have children
                                    var content = thisLinkTarget[l].children.length > 0 ? (thisLinkTarget[l].children[0].nodeValue || ''): thisLinkTarget[l].innerHTML;
                                    // we check we have the dialstring inside the textnode part of the A to avoid replacing all the inner html and overwrite numbers in a sub span/p/...
                                    var regexp = thisDialString.substr(0,1) == '1' ?
                                        // US DialString
                                        '(' + thisDialString.substr(0,1) + ')?' + thisDialString.substr(1) :
                                        // 2 digits index DialStrings like Fr
                                        '(' + thisDialString.substr(0,2) + ')?' + thisDialString.substr(2) + '|' +
                                        // 3 digits index DialStrings like Lu
                                        '(' + thisDialString.substr(0,3) + ')?' + thisDialString.substr(3);
                                    replaceInnerHTML = (new RegExp(regexp)).test(content.replace(/(\d*)[^\d]*(\d*)/g, '$1$2'));
                                }
//                                var replaceInnerHTML = true;
                                if(replaceInnerHTML) {
                                    var original = phonePrefix + iovoxDniApi.numberFormat(thisNumberFormat, thisDialString).replaceAll(/[ ]/g, "(\\s|\\xA0|&nbsp;)*");
                                    var final = phonePrefix + iovoxDniApi.numberFormat(thisNumberFormat, thisNumber);
                                    var innerHtml = '';
                                    try {
                                        innerHtml = thisLinkTarget[l].innerHTML.replace(new RegExp(original, 'g'), final);
                                    } catch (e) {
                                        console.warn(e.message)
                                    }
                                    thisLinkTarget[l].innerHTML = innerHtml || final;
                                }
                            }
                            thisLinkTarget[l].setAttribute('style', 'visibility:visible');
                        }
                    }
                }
            }
        }

        //session id,
        //if we have a session id returned or a session saved id we need to handle it
        if(iovoxNumberData.sessionCode || !!iovoxDniApi.getCookie('iovoxSessionCode')){
            //if the target is set add session code to the page
            if(iovoxApiConfig.sessionCodeTarget) {
                //add the data to the returnData object
                iovoxApiData.returnData.sessionCode = !!iovoxDniApi.getCookie('iovoxSessionCode') ? iovoxDniApi.getCookie('iovoxSessionCode') : iovoxNumberData.sessionCode;
                sessionCodeTarget = document.querySelectorAll(iovoxApiConfig.sessionCodeTarget);
                //update the target html
                for (var m = 0; m < sessionCodeTarget.length; m++) {
                    sessionCodeTarget[m].innerHTML = iovoxApiData.returnData.sessionCode;
                }
            }
            //set the cookie if it doesn't exist
            sessionCodeExp = new Date();
            sessionCodeExp.setDate(sessionCodeExp.getDate()+30); //cookie needs to last 30 days
            if(!iovoxDniApi.getCookie('iovoxSessionCode')) iovoxDniApi.setCookie('iovoxSessionCode', iovoxNumberData.sessionCode, sessionCodeExp);
        }

        //push dataLayer to returnData
        if(iovoxNumberData.dataLayer) iovoxApiData.returnData.dataLayer = iovoxNumberData.dataLayer;

        // iovoxData.returnData = window.iovoxReturnData; //push debug data
        if (iovoxApiConfig.manualNumberUpdate) {
            //trigger custom event for return data
            window.dispatchEvent(new CustomEvent('iovox-js-api-loaded'))
        }
        return true;
    },
    getJSON: function(url, successHandler, errorHandler, postData, contentType) {
        iovoxApiData.xhrData = postData.replace('j=',''); //push debug data

        //set up the xhr request
        var xhr = typeof XMLHttpRequest !== 'undefined' ? new XMLHttpRequest() : new ActiveXObject('Microsoft.XMLHTTP');
        xhr.open('POST', url, true);
        //have to let the api know we are sending data and what type
        xhr.setRequestHeader("Content-type", contentType ? contentType : "application/x-www-form-urlencoded");

        xhr.onreadystatechange = function() {
            var status,
                data;
            if (xhr.readyState === 4) {
                status = xhr.status;
                if (status === 200) {
                    data = JSON.parse(xhr.responseText);
                    successHandler && successHandler(data);
                } else {
                    errorHandler && errorHandler(status);
                }
            }
        };
        xhr.send(postData); //call the php api hook
    },
    getFromNumberPool: function(linkData) {
        var requests = [];
        for (var i = 0; i < linkData.length; i++) {
            requests.push({
                "dialString": linkData[i].dni.dialString,
                "hostname": linkData[i].dni.hostname,
                "numberPool": linkData[i].dni.poolId,
                "siteData": linkData[i].dni.siteData
            });
        }

        var postData = {
            "accessKey": iovoxApiConfig.accessKey,
            "actionKey": iovoxApiConfig.actionKey,
            "numberFormat": iovoxApiConfig.numberFormat ? iovoxApiConfig.numberFormat : iovoxApiConfig.globalNumberFormat,
            "siteData": linkData[0].dni.siteData,
            "hostname": linkData[0].dni.hostname,
            "requests": requests
        };


        if (iovoxApiConfig.accountId) {
            postData.accountId = iovoxApiConfig.accountId;
        }
        if(iovoxApiConfig.sessionKey) {
            postData.sessionKey  = iovoxApiConfig.sessionKey;
        } else if (iovoxApiConfig.source) {
            postData.sessionKey = iovoxDniApi.initPerSourceKey(iovoxApiConfig.source);
        } else if (iovoxApiConfig.sea) {
            postData.sessionKey = iovoxDniApi.initSessionKey();
        } else if (iovoxApiConfig.directory) {
            postData.sessionKey = 'directory';
        }
        iovoxDniApi.getJSON(iovoxApiConfig.apiUri +'/rest/v1/numbers/dynamicnumber/allocate', function (data) {
            // This is to copy the number into the items list, just in case there are multiple items listed for a rotating pool.
            // For now we only support fetching one rotating number on the page, so this will replace it everywhere.
            var dataList = { items: [] };
            for (var i = 0; i < iovoxApiData.requestData.items.length; i++) {
                if(data.numbers && data.numbers[i] !== "No Numbers Available and No Failover Chosen" || data.number) {
                    dataList.items.push({
                        linkid: linkData[i].requestData.linkId,
                        phonenumber: data.number ? String(data.number) : String(data.numbers[i])
                    });
                }
            }
            iovoxDniApi.setVoxNumbers(dataList);
        }, function (results) {
            iovoxDniApi.setVoxNumbers({"items":{}});
            iovoxApiData.statusMessage = results.error; //push debug data
            return false;
        }, JSON.stringify(postData), 'application/json');
    },
    getVoxNumbers: function(linkData) {
        if (linkData.dni.getNumberFromPool) {
            iovoxDniApi.getFromNumberPool(linkData.dni.dnis);
            return true;
        }
        var idList = linkData.iovoxIds,
            postData = {
                "accessKey": iovoxApiConfig.accessKey,
                "actionKey": iovoxApiConfig.actionKey,
                "numberFormat": iovoxApiConfig.adWords ? "xxxxxxxxxxxx" : iovoxApiConfig.numberFormat,
                "requestLinks": idList
            };

        //if using session code option update the post data
        if(iovoxApiConfig.sessionCode){
            if(!iovoxDniApi.getCookie('iovoxSessionCode')){
                postData.getSessionCode = true;
            }
            else {
                postData.sessionCode = iovoxDniApi.getCookie('iovoxSessionCode');
            }
            //set the dataLayer
            postData.dataLayer = iovoxDniApi.getDataLayer();

            //we need to send the adwords number for session documents since it is not looked up
            if(iovoxApiConfig.adWordsNumber) postData.adwordsNumber = iovoxApiConfig.adWordsNumber;
        }
        //set debug data
        iovoxApiData.requestData.sessionCode = postData.sessionCode;

        //make the request
        iovoxDniApi.getJSON(iovoxApiConfig.apiUri +'/rest/v1/numbers/number', function (data) {
            if (data.results.data === "No Content") {
                return iovoxDniApi.setVoxNumbers({"items":{}});
            }
            iovoxDniApi.setVoxNumbers(data.results.data);
            //if debug is set output object to console.
            if(iovoxDniApi.getCookie("iovoxDebug")) console.log(iovoxApiData);
            return true;
        }, function (results) {
            iovoxDniApi.setVoxNumbers({"items":{}});
            iovoxApiData.statusMessage = results.data; //push debug data
            //if debug is set output object to console.
            if(iovoxDniApi.getCookie("iovoxDebug")) console.log(iovoxApiData);
            return false;
        }, JSON.stringify(postData));
    },
    sendApiBeacon: function (platform){
        var postData = {
                "accessKey": iovoxApiConfig.accessKey ? iovoxApiConfig.accessKey : false,
                "actionKey": iovoxApiConfig.actionKey ? iovoxApiConfig.actionKey : false,
                "adWords": iovoxApiConfig.adWords ? iovoxApiConfig.adWords : false,
                "numberFormat": iovoxApiConfig.numberFormat ? iovoxApiConfig.numberFormat : false,
                "adWordsTarget": iovoxApiConfig.adWordsTarget ? iovoxApiConfig.adWordsTarget : false,
                "platform": platform
            },
            beaconModal = document.createElement('div'),
            beaconModalBg = document.createElement('div'),
            beaconModalBody = document.createElement('div'),
            beaconRedirectUrl = 'https://local.rest-store.iovox.com:4443/adwords/setup';

        beaconModalBg.setAttribute('style', 'background:rgba(245,245,245,.7)','top:0', 'left:0', 'display:inline-block;','height:100%', 'width:100%', 'position:fixed' );
        //show the modal
        document.querySelector('body').appendChild(beaconModalBg);

        //set debug data
        iovoxApiData.requestData = postData;

        // TODO remove or switch to endpoint to rest.iovox.com if needed
        iovoxDniApi.getJSON('https://js.iovox.com/api/beacon', function(data) {
            window.location = beaconRedirectUrl;
            iovoxApiData.returnData = data.results.data; //push debug data
            return true;
        }, function(results) {
            window.location = beaconRedirectUrl;
            iovoxApiData.statusCode = results.status;
            iovoxApiData.statusMessage = results.data; //push debug data
            return false;
        }, "j="+ JSON.stringify(postData));
    },
    getVoxIdsByDataAttribute: function(){
        //scrape the data-voxlinkid attributes from the page
        var iovoxDataAttribute = iovoxApiConfig.dataAttribute,
            iovoxIdElements = document.querySelectorAll("["+ iovoxDataAttribute +"]"),
            iovoxIds = [],
            thisRequestData,
            thisLinkId,
            thisSelector;

        if (iovoxIdElements.length) {
            for(var i = 0; i < iovoxIdElements.length; i++) {
                //add the request link info to the request data object
                thisRequestData = {};
                thisLinkId = "";
                thisRequestData.requestId = iovoxIdElements[i].getAttribute(iovoxDataAttribute);
                thisRequestData.linkId = thisLinkId = iovoxApiConfig.checkReferrer ? iovoxDniApi.referrerCheck(iovoxIdElements[i].getAttribute(iovoxDataAttribute)): iovoxIdElements[i].getAttribute(iovoxDataAttribute);
                thisRequestData.selector = "["+ iovoxDataAttribute +"=\""+ iovoxIdElements[i].getAttribute(iovoxDataAttribute) +"\"]";
                thisRequestData.numberFormat = iovoxDniApi.processNumber(document.querySelector(thisRequestData.selector).innerHTML);

                //push request data and voxIds
                iovoxApiData.requestData.items.push(thisRequestData);
                iovoxIds.push(thisLinkId);
                //hide the target element value until call returns.
                thisSelector = document.querySelectorAll(thisRequestData.selector);
                for(var j = 0; j < thisSelector.length; j++){
                    thisSelector[j].setAttribute('style','visibility:hidden');
                }

            }
            return iovoxIds;
        } else {
            return ["noLinksToRequest"];
        }
    },
    collectVoxLinkIds: function(){
        //set up the request objects
        iovoxApiData.requestData = {items:[]};
        var iovoxIds = [],
            thisRequestData,
            thisLinkId,
            thisSelector,
            baseRefDom = {},
            baseRefDomId,
            adWordsTargets,
            uniqRotatingNumberId = 0,
            dni = { getNumberFromPool: false, dnis: [] };

        //hide adwords targets
        if(iovoxApiConfig.adWordsTarget){
            adWordsTargets = document.querySelectorAll(iovoxApiConfig.adWordsTarget);
            for(var i = 0; i < adWordsTargets.length; i++){
                adWordsTargets[i].setAttribute('style','visibility:hidden');
            }
        }

        //check if using window object for linkIds
        if(iovoxApiConfig.requestLinks){
            //collect the linkIds from the voxRequestLinks object
            for(var j = 0; j < iovoxApiConfig.requestLinks.items.length; j++){
                //add the request link info to the request data object
                thisRequestData = {};
                thisLinkId = "";
                //legacy code handling
                if(iovoxApiConfig.requestLinks.items[j].domValue){
                    thisSelector = iovoxApiConfig.requestLinks.items[j].domAttribute === "id" ?
                        "#"+ iovoxApiConfig.requestLinks.items[j].domValue :
                        "."+ iovoxApiConfig.requestLinks.items[j].domValue;
                } else {
                    thisSelector = iovoxApiConfig.requestLinks.items[j].selector;
                }
                thisRequestData.requestId = iovoxApiConfig.requestLinks.items[j].linkId;
                thisRequestData.dialString = iovoxApiConfig.requestLinks.items[j].dialString;
                if(iovoxApiConfig.requestLinks.items[j].oriDialString) {
                    thisRequestData.oriDialString = iovoxApiConfig.requestLinks.items[j].oriDialString;
                }
                thisRequestData.linkId = thisLinkId = iovoxApiConfig.checkReferrer ? iovoxDniApi.referrerCheck(iovoxApiConfig.requestLinks.items[j].linkId) : iovoxApiConfig.requestLinks.items[j].linkId;
                thisRequestData.selector = thisSelector;
                thisRequestData.numberFormat = iovoxDniApi.processNumber(document.querySelector(thisRequestData.selector).innerHTML);

                // Rorating numbers no longer use original number as location information, just pools. This will set request info for rotating number.
                if (thisLinkId === '__ROTATING__') {
                    thisLinkId += (uniqRotatingNumberId++);
                    thisRequestData.linkId = thisLinkId;
                    // If we have a specific pool ID, pull from the pool ID
                    var udni = {};
                    dni.getNumberFromPool = true;
                    udni.siteData = iovoxApiConfig.siteData ? iovoxApiConfig.siteData : {}; // Set site data no matter what
                    if(iovoxApiConfig.sea === true) {
                        var sea = iovoxDniApi.getSeaInformation();
                        for(var i in sea) {
                            udni.siteData[i] = sea[i];
                        }
                        udni.siteData['current_page'] = window.location.href;
                    }
                    if((iovoxApiConfig.sessionKey || iovoxApiConfig.sea) && !iovoxApiConfig.source) {
                        var info = iovoxDniApi.getSessionInformation();
                        udni.siteData._ga = info._ga || '';
                        udni.siteData.adobe = info.adobe || '';
                    }

                    udni.hostname = window.location.host;
                    if (iovoxApiConfig.requestLinks.items[j].poolId || iovoxApiConfig.requestLinks.items[j].dialString) {
                        udni.poolId = iovoxApiConfig.requestLinks.items[j].poolId ? iovoxApiConfig.requestLinks.items[j].poolId : '';
                        udni.dialString = iovoxApiConfig.requestLinks.items[j].dialString ? iovoxApiConfig.requestLinks.items[j].dialString : '';
                    }
                    dni.dnis.push({dni: udni, requestData: thisRequestData});
                }

                //push request data and voxIds
                iovoxApiData.requestData.items.push(thisRequestData);
                iovoxIds.push(thisLinkId);
                //hide the target element value until call returns.
                thisSelector = document.querySelectorAll(thisRequestData.selector);
                for(var k = 0; k < thisSelector.length; k++){
                    thisSelector[k].setAttribute('style','visibility:hidden');
                }
            }
        } else {
            iovoxIds = iovoxDniApi.getVoxIdsByDataAttribute();
        }
        //add base domain referrer
        if(iovoxApiConfig.fallbackReferrer && !!iovoxDniApi.getCookie("iovoxMCM")){
            baseRefDom.requestId = "referringDom";
            baseRefDom.linkId = baseRefDomId = iovoxDniApi.getCookie("iovoxMCM");
            baseRefDom.selector = '';
            iovoxApiData.requestData.items.push(baseRefDom)
            iovoxIds.push(baseRefDomId);
        }
        // iovoxApiData.requestLinkIds = iovoxIds;
        return {iovoxIds:iovoxIds, dni:dni};

    },
    getDataLayer: function(){
        //function to collect data elements from the customer session for storage to elastic session
        var dataLayer = iovoxApiConfig.dataLayer;
        //if no dataLayer is present on the page we need to create a base object and collect some things.
        if(!dataLayer) dataLayer = {};
        //base dataLayer indexes, do not overwrote the customer supplied indexes
        dataLayer.language = dataLayer.language ? dataLayer.language : ( navigator.language || navigator.userLanguage );
        dataLayer.domain = dataLayer.domain ? dataLayer.domain : document.location.origin;
        dataLayer.page =  dataLayer.page ? dataLayer.page : document.location.pathname;
        dataLayer.browser = dataLayer.browser ? dataLayer.browser : iovoxDniApi.getBrowserInfo();
        //return dataLayer to caller method
        return dataLayer;
    },
    getBrowserInfo: function(){
        var nVer = navigator.appVersion;
        var nAgt = navigator.userAgent;
        var browserName  = navigator.appName;
        var fullVersion  = ''+parseFloat(navigator.appVersion);
        var majorVersion = parseInt(navigator.appVersion,10);
        var nameOffset,verOffset,ix;

        // In Opera, the true version is after "Opera" or after "Version"
        if ((verOffset=nAgt.indexOf("Opera"))!=-1) {
            browserName = "Opera";
            fullVersion = nAgt.substring(verOffset+6);
            if ((verOffset=nAgt.indexOf("Version"))!=-1)
                fullVersion = nAgt.substring(verOffset+8);
        }
        // In MSIE, the true version is after "MSIE" in userAgent
        else if ((verOffset=nAgt.indexOf("MSIE"))!=-1) {
            browserName = "Microsoft Internet Explorer";
            fullVersion = nAgt.substring(verOffset+5);
        }
        // In Chrome, the true version is after "Chrome"
        else if ((verOffset=nAgt.indexOf("Chrome"))!=-1) {
            browserName = "Chrome";
            fullVersion = nAgt.substring(verOffset+7);
        }
        // In Safari, the true version is after "Safari" or after "Version"
        else if ((verOffset=nAgt.indexOf("Safari"))!=-1) {
            browserName = "Safari";
            fullVersion = nAgt.substring(verOffset+7);
            if ((verOffset=nAgt.indexOf("Version"))!=-1)
                fullVersion = nAgt.substring(verOffset+8);
        }
        // In Firefox, the true version is after "Firefox"
        else if ((verOffset=nAgt.indexOf("Firefox"))!=-1) {
            browserName = "Firefox";
            fullVersion = nAgt.substring(verOffset+8);
        }
        // In most other browsers, "name/version" is at the end of userAgent
        else if ( (nameOffset=nAgt.lastIndexOf(' ')+1) <
            (verOffset=nAgt.lastIndexOf('/')) )
        {
            browserName = nAgt.substring(nameOffset,verOffset);
            fullVersion = nAgt.substring(verOffset+1);
            if (browserName.toLowerCase()==browserName.toUpperCase()) {
                browserName = navigator.appName;
            }
        }
        // trim the fullVersion string at semicolon/space if present
        if ((ix=fullVersion.indexOf(";"))!=-1)
            fullVersion=fullVersion.substring(0,ix);
        if ((ix=fullVersion.indexOf(" "))!=-1)
            fullVersion=fullVersion.substring(0,ix);

        majorVersion = parseInt(''+fullVersion,10);
        if (isNaN(majorVersion)) {
            fullVersion  = ''+parseFloat(navigator.appVersion);
            majorVersion = parseInt(navigator.appVersion,10);
        }
        return {
            browserName: browserName,
            fullVersion: fullVersion,
            majorVersion: majorVersion,
            appName: navigator.appName,
            userAgent: navigator.userAgent
        }
    },
    adwordsHandler: function(){
        //check for adwords uri param
        if(iovoxDniApi.getParameterByName('iogid')){
            //if there is an adword click update the session cookie
            iovoxApiConfig.adWordsNumber = iovoxDniApi.getParameterByName('iogid');
            //cookie cleanup
            if (!!iovoxDniApi.getCookie("iovoxAdWords")) {
                iovoxDniApi.deleteCookie("iovoxAdWords");
            }
            if(!!iovoxDniApi.getCookie('iovoxMCM')){
                iovoxDniApi.deleteCookie('iovoxMCM');
            }
            //set the cookie for the rest of the session
            iovoxDniApi.setCookie("iovoxAdWords", iovoxApiConfig.adWordsNumber);
            iovoxDniApi.setCookie("iovoxMCM", "PPC");
        } else if(!!iovoxDniApi.getCookie("iovoxAdWords")) {
            iovoxApiConfig.adWordsNumber = iovoxDniApi.getCookie("iovoxAdWords");
        }
    },
    ajaxApiRequest: function(linkId, selector){
        //if we have an on demand ajax style request (ex: modal open)
        //we need to scrape the data and update the request links object to make sure it gets picked up.
        if(linkId && selector) {
            iovoxApiData.iovoxRequestLinks = {
                "items": []
            };
            //check var types for single request or array
            if(typeof linkId !== 'string'){
                for(var i = 0; i < linkId.length; i++) {
                    iovoxApiData.iovoxRequestLinks.items.push({
                        "linkId":linkId[i],
                        "selector": targetType ? (targetType[i] === 'id' ? '#'+ selector[i] : '.'+ selector[i]) : selector[i]
                    });
                }
            } else {
                iovoxApiData.iovoxRequestLinks.items.push({
                    "linkId":linkId,
                    "selector": targetType ? (targetType === 'id' ? '#'+ selector : '.'+ selector) : selector
                });
            }
        }
    },
    setDebug: function(bool){
        if(bool){
            console.log("vox debug mode has been enabled");
            iovoxDniApi.setCookie("iovoxDebug", true);
            console.log(iovoxApiData);
            return true;
        } else {
            console.log('vox debug mode has been disabled');
            iovoxDniApi.deleteCookie("iovoxDebug");
            return false;
        }
    },
    legacySupport: function(){
        //need to handle customers who are using deprecated code and build the new config object.
        if(!window.iovoxApiConfig){
            window.iovoxApiConfig = {};
            iovoxApiConfig.accessKey = window.voxAccessKey;
            iovoxApiConfig.actionKey = window.voxActionKey;
            iovoxApiConfig.adWordsTarget = window.voxAdWordsTarget;
            iovoxApiConfig.apiUri = iovoxApiConfig.apiUri ? iovoxApiConfig.apiUri : 'https://rest.iovox.com';
            iovoxApiConfig.apiVersion = iovoxDniApi.apiVersion +' with deprecated config';
            iovoxApiConfig.checkReferrer = window.voxCheckReferrer;
            iovoxApiConfig.dataAttribute = "data-voxlinkid";
            iovoxApiConfig.dataLayer = window.dataLayer;
            iovoxApiConfig.debug = (window.voxDebug ==='enabled' || !!iovoxDniApi.getCookie('iovoxDebug')) ? true : false;
            iovoxApiConfig.fallbackReferrer = window.voxFallbackReferrer;
            iovoxApiConfig.globalNumberFormat = window.voxNumberFormat ? window.voxNumberFormat : false;
            iovoxApiConfig.manualNumberUpdate = window.voxManualNumberUpdate;
            iovoxApiConfig.referringDomains = window.voxChannelData;
            iovoxApiConfig.replaceLinkId = window.voxReplaceLinkId;
            iovoxApiConfig.requestLinks = window.voxRequestLinks;
            iovoxApiConfig.sessionCode = false;
            iovoxApiConfig.sessionCodeTarget = false;
            iovoxApiConfig.uriMatching = false;
            iovoxApiConfig.siteData = false;
        }
    },
    initialize: function(linkId, selector){
        if(window.iovoxApiConfig) {

            if(iovoxApiConfig.topDomainCookie === true) {
                iovoxApiConfig.forceDomainCookie = '.' + document.location.href.split('.').slice(-2).join('.').replace('/', '');
            } else if(!iovoxApiConfig.forceDomainCookie) {
                iovoxApiConfig.forceDomainCookie = null;
            }
            //get the api uri
            iovoxApiConfig.apiUri = iovoxApiConfig.apiUri ? iovoxApiConfig.apiUri :  'https://rest.iovox.com';
            //set the api version
            iovoxApiConfig.apiVersion = iovoxDniApi.apiVersion;
            //set the api data selector
            iovoxApiConfig.dataAttribute = "data-iovoxlinkid";
            //check is using global number formatting
            iovoxApiConfig.globalNumberFormat = iovoxApiConfig.globalNumberFormat ? iovoxApiConfig.globalNumberFormat : false;
            //check for dataLayer if not included in options
            if(!iovoxApiConfig.dataLayer) iovoxApiConfig.dataLayer = window.iovoxDataLayer ? window.iovoxDataLayer : window.dataLayer;
            //check if uri matching is present in iovoxApiConfig
            iovoxApiConfig.uriMatching = typeof(iovoxApiConfig.uriMatching !== 'undefined') ? iovoxApiConfig.uriMatching : false;
            //check for rotating categories
            iovoxApiConfig.siteData = typeof(iovoxApiConfig.siteData) !== 'undefined'? iovoxApiConfig.siteData : false;
        } else {
            //call the legacy support method to handle deprecated vars and events.
            iovoxDniApi.legacySupport();
        }

        //set the page data object
        window.iovoxApiData = {
            options: iovoxApiConfig
        };

        //handle ajax / on demand style request
        iovoxDniApi.ajaxApiRequest(linkId, selector);

        //call the adwords handler
        iovoxDniApi.adwordsHandler();

        //if we have a beacon request handle it before we call the api
        if(iovoxDniApi.getParameterByName('beacon')){
            iovoxDniApi.sendApiBeacon(iovoxDniApi.getParameterByName('beacon'));
        }

        //set referrer cookie
        iovoxDniApi.setReferrer();

        //collect the link request data and call the api
        iovoxDniApi.getVoxNumbers(iovoxDniApi.collectVoxLinkIds());
    },
    apiVersion: '1.0.0'
};
window.iovoxDniApi.initialize();
