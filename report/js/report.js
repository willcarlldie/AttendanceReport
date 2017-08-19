/*
Written by Tim Ings <tim@tim-ings.com>
Copyright 2017 All rights reserved
 */

var guild;
var realm;
var region;
var wclkey;
var zones = {
    10: false,
    11: false,
    12: false,
    13: false,
    14: false
};
var playerClasses = [
    "DeathKnight",
    "DemonHunter",
    "Druid",
    "Hunter",
    "Mage",
    "Monk",
    "Paladin",
    "Priest",
    "Rogue",
    "Shaman",
    "Warlock",
    "Warrior"
];
var players = [];

function discoverPlayers(report) {
    for (var i = 0; i < report.friendlies.length; i++) {
        var friend = report.friendlies[i];
        if (playerClasses.indexOf(friend.type)) {
            var alreadyInSet = false;
            for (var j = 0; j < players.length; j++) {
                var player = players[j];
                if (player.guid == friend.guid) {
                    alreadyInSet = true;
                    break;
                }
            }
            if (!alreadyInSet) {
                players.push(friend);
            }
        }
    }
}

function parseReport(report) {
    console.log("Parsing report: " + report.title);
    discoverPlayers(report);
}

function fetchFights(reports) {
    console.log("Received " + reports.length + " reports.");
    for (var i = 0; i < reports.length; i++) {
        var report = reports[i];
        var validZone = false;
        for (var zone in zones) {
            if (zones[report.zone]) {
                validZone = true;
                break;
            }
        }
        if (validZone) {
            console.log("Fetching report: " + report.id);
            var request_url = "https://www.warcraftlogs.com:443/v1/report/fights/" + report.id + "?api_key=" + wclkey;
            $.get(request_url, function (reportData) {
                parseReport(reportData);
            });
        }
    }
}

function generateReport() {
    guild = $("#inp-guild").val();
    realm = $("#inp-realm").val();
    region = $("#inp-region").val();
    wclkey = $("#inp-wclkey").val();
    zones["10"] = $("#inp-zone10").is(":checked");
    zones["11"] = $("#inp-zone11").is(":checked");
    zones["12"] = $("#inp-zone12").is(":checked");
    zones["13"] = $("#inp-zone13").is(":checked");

    console.log("Fetching reports for: " + region + "/" + realm + "/" + guild);
    var request_url = "https://www.warcraftlogs.com:443/v1/reports/guild/" + guild + "/" + realm + "/" + region + "?api_key=" + wclkey;
    $.ajax({
        url: request_url,
        type: "GET",
        success: fetchFights,
        statusCode: {
            400: function () {
                alert("Error 400: Unable to find reports for the given guild/realm/region");
            },
            401: function () {
                alert("Error 401: Invalid public key");
            },
            404: function () {
                alert("Error 404: Unable to find reports for the given guild/realm/region");
            }
        },
    });
}

$(function () {
    /*$("#table").bootstrapTable({
        data: data
    });*/
});
