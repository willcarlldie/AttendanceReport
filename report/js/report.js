var guild;
var realm;
var region;
var wclkey;

function parseReport(data, id) {
    console.log("Parsing report: " + id);
    console.log(data["fights"][1])
}

function fetchFights(data) {
    for (var i = 0; i < data.length; i++) {
        var id = data[i]["id"];
        console.log("Fetching report: " + id);
        var request_url = "https://www.warcraftlogs.com:443/v1/report/fights/" + id + "?api_key=" + wclkey;
        $.get(request_url, function(reportData) {
            parseReport(reportData, data[i]);
        });
    }
}

function generateReport() {
    guild = $("#inp-guild").val();
    realm = $("#inp-realm").val();
    region = $("#inp-region").val();
    wclkey = $("#inp-wclkey").val();

    var request_url = "https://www.warcraftlogs.com:443/v1/reports/guild/" + guild + "/" + realm + "/" + region + "?api_key=" + wclkey;
    $.get(request_url, fetchFights);
}

$(function () {
    /*$('#table').bootstrapTable({
        data: data
    });*/
});