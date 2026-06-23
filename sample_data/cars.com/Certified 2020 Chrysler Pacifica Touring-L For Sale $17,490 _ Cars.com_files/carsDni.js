window.carsDni = {
    getCallSourceData: function(){
        return window.callSourceData;
    },
    handleCallSourceData: function(data){
        let dealerPhone;
        let siteData;
        if("undefined" == typeof(data.sellers)){
            //vdp page
            console.log("VDP page");
            dealerPhone = data.seller.phoneNumber.replace(/\D/g, "");
            let item = {linkId: "__ROTATING__", selector: ".dealer-phone, #mobile-call-button", poolId: "1" + dealerPhone, dialString: dealerPhone};
            window.iovoxApiConfig.requestLinks = {items: [item]};
            siteData = data;
            siteData.seller.phoneNumber = dealerPhone;
            siteData = window.carsDni.handleMissingDimensions(siteData);
            window.iovoxApiConfig.siteData = siteData;
        } else {
            //srp page
            console.log("SRP page");
            let buttons = document.querySelectorAll('.contact-by-phone');

            // Add click event listener to each button
            buttons.forEach(function(button) {
                button.addEventListener('click', function(event) {
                    dealerPhone = this.dataset.phoneNumber.replace(/\D/g, "");
                    let item = {linkId: "__ROTATING__", selector:"#" + this.id, poolId: "1" + dealerPhone, dialString: dealerPhone};
                    window.iovoxApiConfig.requestLinks = {items: [item]};
                    siteData = data;
                    if(typeof this.dataset.overridePayload !== 'undefined') {
                        //handle clicked entity site data overrides
                        let overridePayload = JSON.parse(this.dataset.overridePayload);
                        siteData.dimensions.bodyStyle = [overridePayload.bodystyle];
                        siteData.dimensions.make = [overridePayload.make];
                        siteData.dimensions.model = [overridePayload.model];
                        siteData.dimensions.type = [overridePayload.stock_type];
                        siteData.dimensions.listingId = overridePayload.listing_id;
                        siteData.dimensions.price = overridePayload.price;
                        siteData.dimensions.year = overridePayload.model_year;
                    }
                    siteData.dimensions.vin = typeof this.dataset.vin !== 'undefined' ? this.dataset.vin : this.dataset.vim;
                    if(typeof this.dataset.make !== 'undefined') {
                        siteData.dimensions.make = [this.dataset.make];
                    }
                    if(typeof this.dataset.model !== 'undefined') {
                        siteData.dimensions.model = [this.dataset.model];
                    }
                    if(typeof this.dataset.trim !== 'undefined') {
                        siteData.dimensions.trim = [this.dataset.trim];
                    }
                    if(typeof this.dataset.year !== 'undefined') {
                        siteData.dimensions.year = this.dataset.year;
                    }
                    if(typeof this.dataset.listingId !== 'undefined') {
                        siteData.dimensions.listingId = this.dataset.listingId;
                    }

                    //handle clicked entity seller
                    siteData.seller = {
                        "id":window.callSourceData.sellersList[this.dataset.phoneNumber].id,
                        "phoneNumber":dealerPhone,
                        "zicode":""
                    }
                    siteData = window.carsDni.handleMissingDimensions(siteData);
                    window.iovoxApiConfig.siteData = siteData;
                    window.iovoxDniApi.initialize();
                });
            });
        }
    },
    handleMissingDimensions: function (siteData) {
        //check all dimensions required for adf phone leads
        if(typeof siteData.dimensions.bodyStyle === 'undefined' || siteData.dimensions.bodyStyle === null){
            siteData.dimensions.bodyStyle = [];
        }
        if(typeof siteData.dimensions.cylCntId === 'undefined' || siteData.dimensions.cylCntId === null){
            siteData.dimensions.cylCntId = [];
        }
        if(typeof siteData.dimensions.drCntId === 'undefined' || siteData.dimensions.drCntId === null){
            siteData.dimensions.drCntId = [];
        }
        if(typeof siteData.dimensions.drvTrnId === 'undefined' || siteData.dimensions.drvTrnId === null){
            siteData.dimensions.drvTrnId = [];
        }
        if(typeof siteData.dimensions.extColor === 'undefined' || siteData.dimensions.extColor === null){
            siteData.dimensions.extColor = [];
        }
        if(typeof siteData.dimensions.fuelTypeId === 'undefined' || siteData.dimensions.fuelTypeId === null){
            siteData.dimensions.fuelTypeId = [];
        }
        if(typeof siteData.dimensions.intColor === 'undefined' || siteData.dimensions.intColor === null){
            siteData.dimensions.intColor = [];
        }
        if(typeof siteData.dimensions.listingId === 'undefined' || siteData.dimensions.listingId === null){
            siteData.dimensions.listingId = "";
        }
        if(typeof siteData.dimensions.make === 'undefined' || siteData.dimensions.make === null){
            siteData.dimensions.make = [];
        }
        if(typeof siteData.dimensions.mileage === 'undefined' || siteData.dimensions.mileage === null){
            siteData.dimensions.mileage = "";
        }
        if(typeof siteData.dimensions.mlgId === 'undefined' || siteData.dimensions.mlgId === null){
            siteData.dimensions.mlgId = [];
        }
        if(typeof siteData.dimensions.model === 'undefined' || siteData.dimensions.model === null){
            siteData.dimensions.model = [];
        }
        if(typeof siteData.dimensions.normFeatureId === 'undefined' || siteData.dimensions.normFeatureId === null){
            siteData.dimensions.normFeatureId = [];
        }
        if(typeof siteData.dimensions.price === 'undefined' || siteData.dimensions.price === null){
            siteData.dimensions.price = "";
        }
        if(typeof siteData.dimensions.stockNumber === 'undefined' || siteData.dimensions.stockNumber === null){
            siteData.dimensions.stockNumber = "";
        }
        if(typeof siteData.dimensions.transTypeId === 'undefined' || siteData.dimensions.transTypeId === null){
            siteData.dimensions.transTypeId = [];
        }
        if(typeof siteData.dimensions.trim === 'undefined' || siteData.dimensions.trim === null){
            siteData.dimensions.trim = [];
        }
        if(typeof siteData.dimensions.type === 'undefined'){
            siteData.dimensions.type = null;
        }
        if(typeof siteData.dimensions.vin === 'undefined' || siteData.dimensions.vin === null){
            siteData.dimensions.vin = "";
        }
        if(typeof siteData.dimensions.year === 'undefined' || siteData.dimensions.year === null){
            siteData.dimensions.year = "";
        }
        return window.carsDni.handleDimensionDataFormats(siteData);
    },
    handleDimensionDataFormats: function(siteData){
        //check all dimensions data formats required for adf phone leads
        if(siteData.dimensions.bodyStyle.constructor !== Array){
            if(typeof siteData.dimensions.bodyStyle !== 'string'){
                siteData.dimensions.bodyStyle = String(siteData.dimensions.bodyStyle);
            }
            siteData.dimensions.bodyStyle = [siteData.dimensions.bodyStyle];
        }
        if(siteData.dimensions.cylCntId.constructor !== Array){
            if(typeof siteData.dimensions.cylCntId !== 'string'){
                siteData.dimensions.cylCntId = String(siteData.dimensions.cylCntId);
            }
            siteData.dimensions.cylCntId = [siteData.dimensions.cylCntId];
        }
        if(siteData.dimensions.drCntId.constructor !== Array){
            if(typeof siteData.dimensions.drCntId !== 'string'){
                siteData.dimensions.drCntId = String(siteData.dimensions.drCntId);
            }
            siteData.dimensions.drCntId = [siteData.dimensions.drCntId];
        }
        if(siteData.dimensions.drvTrnId.constructor !== Array){
            if(typeof siteData.dimensions.drvTrnId !== 'string'){
                siteData.dimensions.drvTrnId = String(siteData.dimensions.drvTrnId);
            }
            siteData.dimensions.drvTrnId = [siteData.dimensions.drvTrnId];
        }
        if(siteData.dimensions.extColor.constructor !== Array){
            if(typeof siteData.dimensions.extColor !== 'string'){
                siteData.dimensions.extColor = String(siteData.dimensions.extColor);
            }
            siteData.dimensions.extColor = [siteData.dimensions.extColor];
        }
        if(siteData.dimensions.fuelTypeId.constructor !== Array){
            if(typeof siteData.dimensions.fuelTypeId !== 'string'){
                siteData.dimensions.fuelTypeId = String(siteData.dimensions.fuelTypeId);
            }
            siteData.dimensions.fuelTypeId = [siteData.dimensions.fuelTypeId];
        }
        if(siteData.dimensions.intColor.constructor !== Array){
            if(typeof siteData.dimensions.intColor !== 'string'){
                siteData.dimensions.intColor = String(siteData.dimensions.intColor);
            }
            siteData.dimensions.intColor = [siteData.dimensions.intColor];
        }
        if(typeof siteData.dimensions.listingId !== 'string'){
            siteData.dimensions.listingId = String(siteData.dimensions.listingId);
        }
        if(siteData.dimensions.make.constructor !== Array){
            if(typeof siteData.dimensions.make !== 'string'){
                siteData.dimensions.make = String(siteData.dimensions.make);
            }
            siteData.dimensions.make = [siteData.dimensions.make];
        }
        if(typeof siteData.dimensions.mileage !== 'string'){
            siteData.dimensions.mileage = String(siteData.dimensions.mileage);
        }
        if(siteData.dimensions.mlgId.constructor !== Array){
            if(typeof siteData.dimensions.mlgId !== 'string'){
                siteData.dimensions.mlgId = String(siteData.dimensions.mlgId);
            }
            siteData.dimensions.mlgId = [siteData.dimensions.mlgId];
        }
        if(siteData.dimensions.model.constructor !== Array){
            if(typeof siteData.dimensions.model !== 'string'){
                siteData.dimensions.model = String(siteData.dimensions.model);
            }
            siteData.dimensions.model = [siteData.dimensions.model];
        }
        if(siteData.dimensions.normFeatureId.constructor !== Array){
            if(typeof siteData.dimensions.normFeatureId !== 'string'){
                siteData.dimensions.normFeatureId = String(siteData.dimensions.normFeatureId);
            }
            siteData.dimensions.normFeatureId = [siteData.dimensions.normFeatureId];
        }
        if(typeof siteData.dimensions.price !== 'string'){
            siteData.dimensions.price = String(siteData.dimensions.price);
        }
        if(typeof siteData.dimensions.stockNumber !== 'string'){
            siteData.dimensions.stockNumber = String(siteData.dimensions.stockNumber);
        }
        if(siteData.dimensions.transTypeId.constructor !== Array){
            if(typeof siteData.dimensions.transTypeId !== 'string'){
                siteData.dimensions.transTypeId = String(siteData.dimensions.transTypeId);
            }
            siteData.dimensions.transTypeId = [siteData.dimensions.transTypeId];
        }
        if(siteData.dimensions.trim.constructor !== Array){
            if(typeof siteData.dimensions.trim !== 'string'){
                siteData.dimensions.trim = String(siteData.dimensions.trim);
            }
            siteData.dimensions.trim = [siteData.dimensions.trim];
        }
        if(siteData.dimensions.type !== null && siteData.dimensions.type.constructor !== Array){
            if(typeof siteData.dimensions.type !== 'string'){
                siteData.dimensions.type = String(siteData.dimensions.type);
            }
            siteData.dimensions.type = [siteData.dimensions.type];
        }
        if(typeof siteData.dimensions.vin !== 'string'){
            siteData.dimensions.vin = String(siteData.dimensions.vin);
        }
        if(typeof siteData.dimensions.year !== 'string'){
            siteData.dimensions.year = String(siteData.dimensions.year);
        }
      return siteData;
    },
    fetchDniJs: function () {
        window.iovoxApi = document.createElement('script');
        iovoxApi.src = "https://cdn.iovox.com/rest/v1/dni.js";
        document.getElementsByTagName('head')[0].appendChild(iovoxApi);
    },
    replaceNumbers: function () {
        let dniResults = {multisite_ddn: {}};
        let targets = [];
        //check for response data
        if(window.iovoxApiData.returnData.items.length > 0) {
            targets = document.querySelectorAll(window.iovoxApiData.returnData.items[0].selector);
            //if we got a number back update the data
            if (typeof (window.iovoxApiData.returnData.items[0].phoneNumber) !== "undefined") {
                dniResults.multisite_ddn[Number(window.iovoxApiData.returnData.items[0].dialString)] = Number(window.iovoxApiData.returnData.items[0].phoneNumber);
            }
        } else {
            //check for request data
            if(window.iovoxApiData.requestData.items.length > 0){
                targets = document.querySelectorAll(window.iovoxApiData.requestData.items[0].selector);
            }
        }

        if(targets.length > 0) {
            //write the data to the window
            console.log("write number results to window");
            window.iovoxNumbersResult = dniResults;
            //show the phone field
            targets.forEach(target => {
                target.setAttribute('style', 'visibility:visible');
            });
        }
    },
    initialize: function () {
        //set up config
        if("undefined" == typeof(window.iovoxApiConfig)) {
            window.iovoxApiConfig = {
                accessKey:"Yeishie0eipae9TiodeiboJaKu8uC8iu",
                actionKey:"aB7shaag6ooghaiYu2Eej6bu3oizoshu",
                apiUri: "https://rest-us.iovox.com"
            };
        }
        window.iovoxApiConfig.globalNumberFormat = "(xxx) xxx-xxxx";
        window.iovoxApiConfig.sea = true;
        window.iovoxApiConfig.manualNumberUpdate = true;

        //handle callsource data
        this.handleCallSourceData(this.getCallSourceData());
        //fetch dni
        this.fetchDniJs();
        //wait for return data
        window.addEventListener('iovox-js-api-loaded', (event) => {
                this.replaceNumbers();
        });
    }
}

let stateCheck = setInterval(() => {
    if (typeof(window.callSourceData) !== "undefined") {
        clearInterval(stateCheck);
        // document ready
        window.carsDni.initialize();
    }
}, 100);