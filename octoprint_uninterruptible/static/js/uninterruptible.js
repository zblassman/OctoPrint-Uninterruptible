/*
* View model for OctoPrint-Uninterruptible
*
* Author: Zachary Lassman
* License: MIT
*/
$(function() {
    function UninterruptibleViewModel(parameters) {
        var self = this;
        self.settingsViewModel = parameters[0];

        self.statusSettings = {
                'UND': {iconClass: 'fa fa-plug', statusText: 'Undetermined...please wait', unknown: true},
                'UNK': {iconClass: 'fa fa-plug', statusText: 'Unknown', unknown: true},
                'OL': {iconClass: 'fa fa-plug', statusText: 'On Mains', unknown: false},
                'OB': {iconClass: 'fa fa-car-battery', statusText: 'On Battery', unknown: false}
        };

        self.iconClass = ko.observable('');
        self.unknown = ko.observable(false);
        self.dropdownData = ko.observable([]);

        self.state = {status: "UND", percentage: -1, remainingSec: -1};

        self.updateDisplay = function() {
            var statusSetting = self.statusSettings[self.state.status];
            self.iconClass(statusSetting.iconClass);
            self.unknown(statusSetting.unknown);
            var ddata = [{text: "Status: " + statusSetting.statusText }];
            
            if (state.charge != -1) {
                ddata.push({text: "Charge: " + self.state.charge + "%"})
            }
            if (state.runtime != -1) {
                var total_m = Math.round(self.state.runtime / 60);
                var m = total_m % 60;
                var h = (total_m - m) / 60;
                var hhmm = (h<10?"0":"") + h.toString() + (m<10?":0":":") + m.toString();
                ddata.push({text: "Remaining: " + hhmm + "h"})
            }

            self.dropdownData(ddata);
        };


        self.requestData = function() {
            OctoPrint.plugins.uninterruptible.get()
                .done(function(response) {
                    self.state = response;
                    self.updateDisplay();
                })
        };

        self.updateDisplay();

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin != "uninterruptible") {
                return;
            }
            self.state = data;
            self.updateDisplay();

        };

        self.onStartup = self.onServerReconnect = function() {
            self.requestData();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
            construct: UninterruptibleViewModel,
            dependencies: ["settingsViewModel"],
            elements: ["#navbar_plugin_uninterruptible"]
    });
});
