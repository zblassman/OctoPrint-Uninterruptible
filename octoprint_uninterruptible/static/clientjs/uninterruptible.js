(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var OctoPrintUninterruptibleClient = function(base) {
        this.base = base;
    };

    OctoPrintUninterruptibleClient.prototype.get = function(opts) {
        return this.base.get(this.base.getSimpleApiUrl("uninterruptible"));
    };

    OctoPrintClient.registerPluginComponent("uninterruptible", OctoPrintUninterruptibleClient);
    return OctoPrintUninterruptibleClient;
});