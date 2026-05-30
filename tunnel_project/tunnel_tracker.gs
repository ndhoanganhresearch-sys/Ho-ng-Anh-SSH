/**
 * tunnel_tracker.gs - Google Apps Script endpoint for the SSL Smart Tunnel
 * Monitoring System (4D-LiDAR).
 *
 * Receives deformation monitoring campaign rows produced by sheet_tracker.py
 * (MonitoringTracker) and appends them to a Google Sheet, colouring each
 * campaign by its alert status so settlement / convergence trends are visible
 * at a glance.
 *
 * Deploy: Extensions > Apps Script > Deploy > New deployment > Web app.
 *   - Execute as: Me
 *   - Who has access: Anyone with the link (or restrict to your domain)
 * Then POST JSON to the /exec URL:
 *   { "secret": "<SHARED_SECRET>",
 *     "campaign": { "label": "T2", "timestamp": "2026-03-01T00:00:00Z",
 *                   "crown_settlement_mm": 28.0, ... , "overall_status": "critical" } }
 */

// Set a shared secret in Project Settings > Script properties (key: SHARED_SECRET).
var SHEET_NAME = 'Deformation Log';

var HEADERS = [
  'label', 'timestamp',
  'crown_settlement_mm', 'crown_settlement_mm_status',
  'lateral_convergence_mm', 'lateral_convergence_mm_status',
  'ovality_mean_pct', 'ovality_mean_pct_status',
  'eccentricity_mean_mm', 'eccentricity_mean_mm_status',
  'overall_status'
];

var STATUS_COLORS = {
  ok:       '#D1FAE5',  // green-100
  caution:  '#FEF3C7',  // amber-100
  critical: '#FEE2E2',  // red-100
  'n/a':    '#F1F5F9'   // slate-100
};

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return _json({ ok: false, error: 'No POST body.' });
    }
    var payload = JSON.parse(e.postData.contents);

    var expected = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (expected && payload.secret !== expected) {
      return _json({ ok: false, error: 'Unauthorized.' });
    }

    var campaign = payload.campaign;
    if (!campaign || !campaign.label) {
      return _json({ ok: false, error: 'Missing campaign.label.' });
    }

    var sheet = _getSheet();
    var row = HEADERS.map(function (key) {
      return campaign[key] !== undefined && campaign[key] !== null ? campaign[key] : '';
    });
    sheet.appendRow(row);

    var lastRow = sheet.getLastRow();
    var status = campaign.overall_status || 'n/a';
    var color = STATUS_COLORS[status] || STATUS_COLORS['n/a'];
    sheet.getRange(lastRow, 1, 1, HEADERS.length).setBackground(color);

    return _json({ ok: true, row: lastRow, status: status });
  } catch (err) {
    return _json({ ok: false, error: String(err) });
  }
}

function doGet() {
  var sheet = _getSheet();
  var values = sheet.getDataRange().getValues();
  return _json({ ok: true, rows: values.length - 1, headers: HEADERS });
}

function _getSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
  }
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function _json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
