#!/usr/bin/env node
/**
 * Generate the podcast edit review HTML from transcript data + template.
 *
 * Usage:
 *   node generate_edit_review.js [options]
 *     --transcript   Formatted transcript .txt path (Speaker: text per line)
 *     --edit-decision  edit_decision.json path (alternative to transcript)
 *     --proposal     edit_proposal.md path (optional, for AI suggestion preloading)
 *     --audio        Audio file relative path for the HTML (informational only)
 *     --guest        Guest name
 *     --host         Host name (default: Host)
 *     --output       Output HTML path (default: podcast_output/edit_review.html)
 *     --title        Page title (default: Podcast Edit Review)
 *
 * This script does NOT use child_process or shell commands.
 * The only .exec() calls are RegExp.prototype.exec() for pattern matching.
 */

const fs = require('fs');
const path = require('path');

// ── Parse CLI arguments ──────────────────────────────────────────────────
const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i].replace('--', '');
  args[key] = process.argv[i + 1];
}

const transcriptFile = args.transcript || null;
const editDecisionFile = args['edit-decision'] || null;
const proposalFile = args.proposal || null;
const audioSrc = args.audio || '';
const guestName = args.guest || 'Guest';
const hostName = args.host || 'Host';
const outputFile = args.output || 'podcast_output/edit_review.html';
const pageTitle = args.title || 'Podcast Edit Review';

// ── Helpers ──────────────────────────────────────────────────────────────
function fmtHMS(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}

function parseTimeStr(ts) {
  const parts = ts.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] || 0;
}

function escapeForHTML(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Locate template ──────────────────────────────────────────────────────
const scriptDir = path.dirname(process.argv[1] || __filename);
const templateFile = path.resolve(scriptDir, '../templates/edit_review.html');

if (!fs.existsSync(templateFile)) {
  console.error('ERROR: Template not found at ' + templateFile);
  process.exit(1);
}

// ── Parse segments ───────────────────────────────────────────────────────
let segments = [];

if (editDecisionFile && fs.existsSync(editDecisionFile)) {
  console.log('Reading edit_decision.json: ' + editDecisionFile);
  const data = JSON.parse(fs.readFileSync(editDecisionFile, 'utf8'));

  if (data.segments) {
    segments = data.segments.map(function(seg, idx) {
      return {
        id: seg.id || 'seg_' + String(idx + 1).padStart(3, '0'),
        speaker: seg.speaker || 'Unknown',
        text: seg.edited_text || seg.original_text || seg.text || '',
        original_text: seg.original_text || seg.text || '',
        edited_text: seg.edited_text || '',
        start_time: seg.start_time || '00:00:00',
        end_time: seg.end_time || '00:00:00',
        original_position: seg.original_position || idx + 1,
        status: seg.status || 'keep',
        muted_ranges: seg.muted_ranges || [],
        act: seg.act || null,
        is_key_moment: seg.is_key_moment || false,
        source: seg.source || null,
        suggested: false,
        suggestion_info: null
      };
    });
  } else if (Array.isArray(data)) {
    let segIdx = 0;
    data.forEach(function(entry) {
      const act = entry.act || null;
      const src = entry.source || null;
      const isKey = entry.is_key_moment || false;

      if (entry.host_question) {
        segIdx++;
        const hq = entry.host_question;
        segments.push({
          id: 'seg_' + String(segIdx).padStart(3, '0'),
          speaker: hostName,
          text: hq.edited || hq.original || hq.text || '',
          original_text: hq.original || hq.text || '',
          edited_text: hq.edited || '',
          start_time: hq.start_time || '00:00:00',
          end_time: hq.end_time || '00:00:00',
          original_position: segIdx,
          status: entry.status || 'keep',
          muted_ranges: [],
          act: act,
          is_key_moment: isKey,
          source: src,
          suggested: false,
          suggestion_info: null
        });
      }

      if (entry.guest_answer) {
        segIdx++;
        const ga = entry.guest_answer;
        segments.push({
          id: 'seg_' + String(segIdx).padStart(3, '0'),
          speaker: guestName,
          text: ga.edited || ga.original || ga.text || '',
          original_text: ga.original || ga.text || '',
          edited_text: ga.edited || '',
          start_time: ga.start_time || '00:00:00',
          end_time: ga.end_time || '00:00:00',
          original_position: segIdx,
          status: entry.status || 'keep',
          muted_ranges: [],
          act: act,
          is_key_moment: isKey,
          source: src,
          suggested: false,
          suggestion_info: null
        });
      }
    });
  }

} else if (transcriptFile && fs.existsSync(transcriptFile)) {
  console.log('Reading transcript: ' + transcriptFile);
  const lines = fs.readFileSync(transcriptFile, 'utf8')
    .split('\n')
    .filter(function(l) { return l.trim(); });

  let segIdx = 0;
  let currentTime = 0;

  lines.forEach(function(line) {
    segIdx++;
    let speaker = 'Unknown';
    let text = line.trim();

    const colonIdx = text.indexOf(':');
    if (colonIdx > 0 && colonIdx < 30) {
      const possibleSpeaker = text.substring(0, colonIdx).trim();
      if (possibleSpeaker.indexOf(' ') === -1 || possibleSpeaker.length < 20) {
        speaker = possibleSpeaker;
        text = text.substring(colonIdx + 1).trim();
      }
    }

    if (speaker.toLowerCase().indexOf('host') !== -1 || speaker === hostName) {
      speaker = hostName;
    } else if (speaker.toLowerCase().indexOf('guest') !== -1 || speaker === guestName) {
      speaker = guestName;
    }

    const duration = Math.max(1, text.length / 15);
    const startSec = currentTime;
    const endSec = currentTime + duration;

    segments.push({
      id: 'seg_' + String(segIdx).padStart(3, '0'),
      speaker: speaker,
      text: text,
      original_text: text,
      edited_text: '',
      start_time: fmtHMS(startSec),
      end_time: fmtHMS(endSec),
      original_position: segIdx,
      status: 'keep',
      muted_ranges: [],
      act: null,
      is_key_moment: false,
      source: null,
      suggested: false,
      suggestion_info: null
    });

    currentTime = endSec;
  });

} else {
  console.error('ERROR: Provide --transcript or --edit-decision');
  process.exit(1);
}

console.log('Parsed ' + segments.length + ' segments');

// ── Parse and apply AI suggestions from edit_proposal.md ─────────────────
if (proposalFile && fs.existsSync(proposalFile)) {
  console.log('Reading proposal: ' + proposalFile);
  const proposalText = fs.readFileSync(proposalFile, 'utf8');
  const cuts = [];
  // Use matchAll to find CUT headers in the proposal markdown
  const allMatches = proposalText.matchAll(
    /###\s+CUT\s+(\d+):\s+(.+?)\s*\((\d[\d:]+)\s*[–\-]\s*(\d[\d:]+)\)/g
  );
  for (const match of allMatches) {
    const afterText = proposalText.substring(match.index + match[0].length);
    const ratMatch = afterText.match(/\*\*Rationale:\*\*\s*(.+?)(?=\n\*\*Saves:|\n###|\n## )/s);

    cuts.push({
      cut_num: parseInt(match[1]),
      label: match[2].trim(),
      start: parseTimeStr(match[3]),
      end: parseTimeStr(match[4]),
      rationale: ratMatch ? ratMatch[1].trim() : ''
    });
  }

  console.log('Found ' + cuts.length + ' cuts in proposal');

  let mapped = 0;
  segments.forEach(function(seg) {
    const segStart = parseTimeStr(seg.start_time);
    const segEnd = parseTimeStr(seg.end_time);

    for (let c = 0; c < cuts.length; c++) {
      if (Math.max(segStart, cuts[c].start) < Math.min(segEnd, cuts[c].end)) {
        seg.status = 'cut';
        seg.suggested = true;
        seg.suggestion_info = {
          cut_num: cuts[c].cut_num,
          label: cuts[c].label,
          rationale: cuts[c].rationale
        };
        mapped++;
        break;
      }
    }
  });

  console.log('Mapped ' + mapped + ' segments to AI suggestions');
}

// ── Build show config ────────────────────────────────────────────────────
const showConfig = {
  host_name: hostName,
  guest_name: guestName,
  audio_src: audioSrc
};

// ── Inject into template ─────────────────────────────────────────────────
console.log('Injecting data into template...');
let html = fs.readFileSync(templateFile, 'utf8');

html = html.replace('__TITLE__', escapeForHTML(pageTitle));
html = html.replace('__SEGMENTS_DATA__', JSON.stringify(segments));
html = html.replace('__SHOW_CONFIG__', JSON.stringify(showConfig));

// ── Write output ─────────────────────────────────────────────────────────
const outputDir = path.dirname(outputFile);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

fs.writeFileSync(outputFile, html, 'utf8');
console.log('Generated: ' + outputFile);
console.log('  Segments: ' + segments.length);
console.log('  Suggestions: ' + segments.filter(function(s) { return s.suggested; }).length);
