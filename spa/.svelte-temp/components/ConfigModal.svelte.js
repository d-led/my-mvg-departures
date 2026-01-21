import 'svelte/internal/disclose-version';

ConfigModal[$.FILENAME] = 'src/components/ConfigModal.svelte';

import * as $ from 'svelte/internal/client';
import { onMount } from "svelte";

var root = $.add_locations($.from_html(`<div class="modal-overlay svelte-ha7zfr"><div class="modal-content svelte-ha7zfr"><div class="modal-header svelte-ha7zfr"><h2 class="svelte-ha7zfr">Configuration</h2> <button class="close-button svelte-ha7zfr" aria-label="Close">×</button></div> <div class="modal-body svelte-ha7zfr"><p>Paste your TOML configuration below:</p> <textarea class="config-textarea svelte-ha7zfr" placeholder="Paste TOML config here..." rows="20"></textarea></div> <div class="modal-footer svelte-ha7zfr"><button class="button button-secondary svelte-ha7zfr">Cancel</button> <button class="button button-primary svelte-ha7zfr">Save</button></div></div></div>`), ConfigModal[$.FILENAME], [
	[
		36,
		0,
		[
			[
				37,
				2,
				[
					[38, 4, [[39, 6], [40, 6]]],
					[42, 4, [[43, 6], [44, 6]]],
					[51, 4, [[52, 6], [53, 6]]]
				]
			]
		]
	]
]);

const $$css = {
	hash: 'svelte-ha7zfr',
	code: '\n  .modal-overlay.svelte-ha7zfr {\n    position: fixed;\n    top: 0;\n    left: 0;\n    right: 0;\n    bottom: 0;\n    background-color: rgba(0, 0, 0, 0.5);\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    z-index: 10000;\n  }\n\n  .modal-content.svelte-ha7zfr {\n    background: white;\n    border-radius: 0.5rem;\n    padding: 1.5rem;\n    max-width: 90vw;\n    max-height: 90vh;\n    width: 800px;\n    display: flex;\n    flex-direction: column;\n    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);\n  }\n\n  /* (unused) [data-theme="dark"] .modal-content {\n    background: #1d232a;\n    color: #f9fafb;\n  }*/\n\n  .modal-header.svelte-ha7zfr {\n    display: flex;\n    justify-content: space-between;\n    align-items: center;\n    margin-bottom: 1rem;\n  }\n\n  .modal-header.svelte-ha7zfr h2:where(.svelte-ha7zfr) {\n    margin: 0;\n    font-size: 1.5rem;\n    font-weight: 700;\n  }\n\n  .close-button.svelte-ha7zfr {\n    background: none;\n    border: none;\n    font-size: 2rem;\n    cursor: pointer;\n    padding: 0;\n    width: 2rem;\n    height: 2rem;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    color: #6b7280;\n  }\n\n  .close-button.svelte-ha7zfr:hover {\n    color: #111827;\n  }\n\n  /* (unused) [data-theme="dark"] .close-button {\n    color: #9ca3af;\n  }*/\n\n  /* (unused) [data-theme="dark"] .close-button:hover {\n    color: #f9fafb;\n  }*/\n\n  .modal-body.svelte-ha7zfr {\n    flex: 1;\n    overflow-y: auto;\n    margin-bottom: 1rem;\n  }\n\n  .config-textarea.svelte-ha7zfr {\n    width: 100%;\n    min-height: 400px;\n    font-family: monospace;\n    font-size: 0.875rem;\n    padding: 0.75rem;\n    border: 1px solid #d1d5db;\n    border-radius: 0.375rem;\n    resize: vertical;\n    box-sizing: border-box;\n  }\n\n  /* (unused) [data-theme="dark"] .config-textarea {\n    background: #111827;\n    color: #f9fafb;\n    border-color: #374151;\n  }*/\n\n  .modal-footer.svelte-ha7zfr {\n    display: flex;\n    justify-content: flex-end;\n    gap: 0.75rem;\n  }\n\n  .button.svelte-ha7zfr {\n    padding: 0.5rem 1rem;\n    border-radius: 0.375rem;\n    font-weight: 500;\n    cursor: pointer;\n    border: none;\n    transition: background-color 0.2s;\n  }\n\n  .button.svelte-ha7zfr:disabled {\n    opacity: 0.5;\n    cursor: not-allowed;\n  }\n\n  .button-primary.svelte-ha7zfr {\n    background-color: #087BC4;\n    color: white;\n  }\n\n  .button-primary.svelte-ha7zfr:hover:not(:disabled) {\n    background-color: #0669a3;\n  }\n\n  .button-secondary.svelte-ha7zfr {\n    background-color: #e5e7eb;\n    color: #111827;\n  }\n\n  .button-secondary.svelte-ha7zfr:hover {\n    background-color: #d1d5db;\n  }\n\n  /* (unused) [data-theme="dark"] .button-secondary {\n    background-color: #374151;\n    color: #f9fafb;\n  }*/\n\n  /* (unused) [data-theme="dark"] .button-secondary:hover {\n    background-color: #4b5563;\n  }*/\n\n/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiQ29uZmlnTW9kYWwuc3ZlbHRlIiwic291cmNlcyI6WyJDb25maWdNb2RhbC5zdmVsdGUiXSwic291cmNlc0NvbnRlbnQiOlsiPHNjcmlwdCBsYW5nPVwidHNcIj5cbiAgaW1wb3J0IHsgb25Nb3VudCB9IGZyb20gXCJzdmVsdGVcIjtcblxuICBsZXQge1xuICAgIGN1cnJlbnRDb25maWcgPSBudWxsLFxuICAgIG9uU2F2ZSxcbiAgICBvbkNhbmNlbCxcbiAgfToge1xuICAgIGN1cnJlbnRDb25maWc/OiB1bmtub3duO1xuICAgIG9uU2F2ZTogKGNvbmZpZzogc3RyaW5nKSA9PiB2b2lkO1xuICAgIG9uQ2FuY2VsOiAoKSA9PiB2b2lkO1xuICB9ID0gJHByb3BzKCk7XG5cbiAgbGV0IGNvbmZpZ1RleHQgPSAkc3RhdGUoXCJcIik7XG5cbiAgb25Nb3VudCgoKSA9PiB7XG4gICAgLy8gTG9hZCBjdXJyZW50IGNvbmZpZyBhcyBUT01MIHN0cmluZyBpZiBhdmFpbGFibGVcbiAgICAvLyBGb3Igbm93LCB3ZSdsbCBqdXN0IHNob3cgYW4gZW1wdHkgdGV4dGFyZWFcbiAgICAvLyBJbiBhIHJlYWwgaW1wbGVtZW50YXRpb24sIHlvdSdkIGNvbnZlcnQgdGhlIGNvbmZpZyBiYWNrIHRvIFRPTUxcbiAgICBjb25maWdUZXh0ID0gXCJcIjtcbiAgfSk7XG5cbiAgZnVuY3Rpb24gaGFuZGxlU2F2ZSgpIHtcbiAgICBpZiAoY29uZmlnVGV4dC50cmltKCkpIHtcbiAgICAgIG9uU2F2ZShjb25maWdUZXh0KTtcbiAgICB9XG4gIH1cblxuICBmdW5jdGlvbiBoYW5kbGVLZXlkb3duKGV2ZW50OiBLZXlib2FyZEV2ZW50KSB7XG4gICAgaWYgKGV2ZW50LmtleSA9PT0gXCJFc2NhcGVcIikge1xuICAgICAgb25DYW5jZWwoKTtcbiAgICB9XG4gIH1cbjwvc2NyaXB0PlxuXG48ZGl2IGNsYXNzPVwibW9kYWwtb3ZlcmxheVwiIG9uY2xpY2s9e29uQ2FuY2VsfSBvbmtleWRvd249e2hhbmRsZUtleWRvd259PlxuICA8ZGl2IGNsYXNzPVwibW9kYWwtY29udGVudFwiIG9uY2xpY2s9eyhlKSA9PiBlLnN0b3BQcm9wYWdhdGlvbigpfT5cbiAgICA8ZGl2IGNsYXNzPVwibW9kYWwtaGVhZGVyXCI+XG4gICAgICA8aDI+Q29uZmlndXJhdGlvbjwvaDI+XG4gICAgICA8YnV0dG9uIGNsYXNzPVwiY2xvc2UtYnV0dG9uXCIgb25jbGljaz17b25DYW5jZWx9IGFyaWEtbGFiZWw9XCJDbG9zZVwiPsOXPC9idXR0b24+XG4gICAgPC9kaXY+XG4gICAgPGRpdiBjbGFzcz1cIm1vZGFsLWJvZHlcIj5cbiAgICAgIDxwPlBhc3RlIHlvdXIgVE9NTCBjb25maWd1cmF0aW9uIGJlbG93OjwvcD5cbiAgICAgIDx0ZXh0YXJlYVxuICAgICAgICBiaW5kOnZhbHVlPXtjb25maWdUZXh0fVxuICAgICAgICBjbGFzcz1cImNvbmZpZy10ZXh0YXJlYVwiXG4gICAgICAgIHBsYWNlaG9sZGVyPVwiUGFzdGUgVE9NTCBjb25maWcgaGVyZS4uLlwiXG4gICAgICAgIHJvd3M9XCIyMFwiXG4gICAgICA+PC90ZXh0YXJlYT5cbiAgICA8L2Rpdj5cbiAgICA8ZGl2IGNsYXNzPVwibW9kYWwtZm9vdGVyXCI+XG4gICAgICA8YnV0dG9uIGNsYXNzPVwiYnV0dG9uIGJ1dHRvbi1zZWNvbmRhcnlcIiBvbmNsaWNrPXtvbkNhbmNlbH0+Q2FuY2VsPC9idXR0b24+XG4gICAgICA8YnV0dG9uIGNsYXNzPVwiYnV0dG9uIGJ1dHRvbi1wcmltYXJ5XCIgb25jbGljaz17aGFuZGxlU2F2ZX0gZGlzYWJsZWQ9eyFjb25maWdUZXh0LnRyaW0oKX0+XG4gICAgICAgIFNhdmVcbiAgICAgIDwvYnV0dG9uPlxuICAgIDwvZGl2PlxuICA8L2Rpdj5cbjwvZGl2PlxuXG48c3R5bGU+XG4gIC5tb2RhbC1vdmVybGF5IHtcbiAgICBwb3NpdGlvbjogZml4ZWQ7XG4gICAgdG9wOiAwO1xuICAgIGxlZnQ6IDA7XG4gICAgcmlnaHQ6IDA7XG4gICAgYm90dG9tOiAwO1xuICAgIGJhY2tncm91bmQtY29sb3I6IHJnYmEoMCwgMCwgMCwgMC41KTtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7XG4gICAgei1pbmRleDogMTAwMDA7XG4gIH1cblxuICAubW9kYWwtY29udGVudCB7XG4gICAgYmFja2dyb3VuZDogd2hpdGU7XG4gICAgYm9yZGVyLXJhZGl1czogMC41cmVtO1xuICAgIHBhZGRpbmc6IDEuNXJlbTtcbiAgICBtYXgtd2lkdGg6IDkwdnc7XG4gICAgbWF4LWhlaWdodDogOTB2aDtcbiAgICB3aWR0aDogODAwcHg7XG4gICAgZGlzcGxheTogZmxleDtcbiAgICBmbGV4LWRpcmVjdGlvbjogY29sdW1uO1xuICAgIGJveC1zaGFkb3c6IDAgMjBweCAyNXB4IC01cHggcmdiYSgwLCAwLCAwLCAwLjEpO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5tb2RhbC1jb250ZW50IHtcbiAgICBiYWNrZ3JvdW5kOiAjMWQyMzJhO1xuICAgIGNvbG9yOiAjZjlmYWZiO1xuICB9XG5cbiAgLm1vZGFsLWhlYWRlciB7XG4gICAgZGlzcGxheTogZmxleDtcbiAgICBqdXN0aWZ5LWNvbnRlbnQ6IHNwYWNlLWJldHdlZW47XG4gICAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAgICBtYXJnaW4tYm90dG9tOiAxcmVtO1xuICB9XG5cbiAgLm1vZGFsLWhlYWRlciBoMiB7XG4gICAgbWFyZ2luOiAwO1xuICAgIGZvbnQtc2l6ZTogMS41cmVtO1xuICAgIGZvbnQtd2VpZ2h0OiA3MDA7XG4gIH1cblxuICAuY2xvc2UtYnV0dG9uIHtcbiAgICBiYWNrZ3JvdW5kOiBub25lO1xuICAgIGJvcmRlcjogbm9uZTtcbiAgICBmb250LXNpemU6IDJyZW07XG4gICAgY3Vyc29yOiBwb2ludGVyO1xuICAgIHBhZGRpbmc6IDA7XG4gICAgd2lkdGg6IDJyZW07XG4gICAgaGVpZ2h0OiAycmVtO1xuICAgIGRpc3BsYXk6IGZsZXg7XG4gICAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjtcbiAgICBjb2xvcjogIzZiNzI4MDtcbiAgfVxuXG4gIC5jbG9zZS1idXR0b246aG92ZXIge1xuICAgIGNvbG9yOiAjMTExODI3O1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5jbG9zZS1idXR0b24ge1xuICAgIGNvbG9yOiAjOWNhM2FmO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5jbG9zZS1idXR0b246aG92ZXIge1xuICAgIGNvbG9yOiAjZjlmYWZiO1xuICB9XG5cbiAgLm1vZGFsLWJvZHkge1xuICAgIGZsZXg6IDE7XG4gICAgb3ZlcmZsb3cteTogYXV0bztcbiAgICBtYXJnaW4tYm90dG9tOiAxcmVtO1xuICB9XG5cbiAgLmNvbmZpZy10ZXh0YXJlYSB7XG4gICAgd2lkdGg6IDEwMCU7XG4gICAgbWluLWhlaWdodDogNDAwcHg7XG4gICAgZm9udC1mYW1pbHk6IG1vbm9zcGFjZTtcbiAgICBmb250LXNpemU6IDAuODc1cmVtO1xuICAgIHBhZGRpbmc6IDAuNzVyZW07XG4gICAgYm9yZGVyOiAxcHggc29saWQgI2QxZDVkYjtcbiAgICBib3JkZXItcmFkaXVzOiAwLjM3NXJlbTtcbiAgICByZXNpemU6IHZlcnRpY2FsO1xuICAgIGJveC1zaXppbmc6IGJvcmRlci1ib3g7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImRhcmtcIl0gLmNvbmZpZy10ZXh0YXJlYSB7XG4gICAgYmFja2dyb3VuZDogIzExMTgyNztcbiAgICBjb2xvcjogI2Y5ZmFmYjtcbiAgICBib3JkZXItY29sb3I6ICMzNzQxNTE7XG4gIH1cblxuICAubW9kYWwtZm9vdGVyIHtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGp1c3RpZnktY29udGVudDogZmxleC1lbmQ7XG4gICAgZ2FwOiAwLjc1cmVtO1xuICB9XG5cbiAgLmJ1dHRvbiB7XG4gICAgcGFkZGluZzogMC41cmVtIDFyZW07XG4gICAgYm9yZGVyLXJhZGl1czogMC4zNzVyZW07XG4gICAgZm9udC13ZWlnaHQ6IDUwMDtcbiAgICBjdXJzb3I6IHBvaW50ZXI7XG4gICAgYm9yZGVyOiBub25lO1xuICAgIHRyYW5zaXRpb246IGJhY2tncm91bmQtY29sb3IgMC4ycztcbiAgfVxuXG4gIC5idXR0b246ZGlzYWJsZWQge1xuICAgIG9wYWNpdHk6IDAuNTtcbiAgICBjdXJzb3I6IG5vdC1hbGxvd2VkO1xuICB9XG5cbiAgLmJ1dHRvbi1wcmltYXJ5IHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjMDg3QkM0O1xuICAgIGNvbG9yOiB3aGl0ZTtcbiAgfVxuXG4gIC5idXR0b24tcHJpbWFyeTpob3Zlcjpub3QoOmRpc2FibGVkKSB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzA2NjlhMztcbiAgfVxuXG4gIC5idXR0b24tc2Vjb25kYXJ5IHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjZTVlN2ViO1xuICAgIGNvbG9yOiAjMTExODI3O1xuICB9XG5cbiAgLmJ1dHRvbi1zZWNvbmRhcnk6aG92ZXIge1xuICAgIGJhY2tncm91bmQtY29sb3I6ICNkMWQ1ZGI7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImRhcmtcIl0gLmJ1dHRvbi1zZWNvbmRhcnkge1xuICAgIGJhY2tncm91bmQtY29sb3I6ICMzNzQxNTE7XG4gICAgY29sb3I6ICNmOWZhZmI7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImRhcmtcIl0gLmJ1dHRvbi1zZWNvbmRhcnk6aG92ZXIge1xuICAgIGJhY2tncm91bmQtY29sb3I6ICM0YjU1NjM7XG4gIH1cbjwvc3R5bGU+XG4iXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IjtBQTREQSxFQUFFLDRCQUFjLENBQUM7QUFDakIsSUFBSSxlQUFlO0FBQ25CLElBQUksTUFBTTtBQUNWLElBQUksT0FBTztBQUNYLElBQUksUUFBUTtBQUNaLElBQUksU0FBUztBQUNiLElBQUksb0NBQW9DO0FBQ3hD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 */'
};

export default function ConfigModal($$anchor, $$props) {
	$.check_target(new.target);
	$.push($$props, true, ConfigModal);
	$.append_styles($$anchor, $$css);

	let currentConfig = $.prop($$props, 'currentConfig', 3, null);
	let configText = $.tag($.state(""), 'configText');

	onMount(() => {
		// Load current config as TOML string if available
		// For now, we'll just show an empty textarea
		// In a real implementation, you'd convert the config back to TOML
		$.set(configText, "");
	});

	function handleSave() {
		if ($.get(configText).trim()) {
			$$props.onSave($.get(configText));
		}
	}

	function handleKeydown(event) {
		if ($.strict_equals(event.key, "Escape")) {
			$$props.onCancel();
		}
	}

	var $$exports = { ...$.legacy_api() };
	var div = root();

	div.__click = function (...$$args) {
		$.apply(() => $$props.onCancel, this, $$args, ConfigModal, [36, 36]);
	};

	div.__keydown = handleKeydown;

	var div_1 = $.child(div);

	div_1.__click = (e) => e.stopPropagation();

	var div_2 = $.child(div_1);
	var button = $.sibling($.child(div_2), 2);

	button.__click = function (...$$args) {
		$.apply(() => $$props.onCancel, this, $$args, ConfigModal, [40, 44]);
	};

	$.reset(div_2);

	var div_3 = $.sibling(div_2, 2);
	var textarea = $.sibling($.child(div_3), 2);

	$.remove_textarea_child(textarea);
	$.reset(div_3);

	var div_4 = $.sibling(div_3, 2);
	var button_1 = $.child(div_4);

	button_1.__click = function (...$$args) {
		$.apply(() => $$props.onCancel, this, $$args, ConfigModal, [52, 55]);
	};

	var button_2 = $.sibling(button_1, 2);

	button_2.__click = handleSave;
	$.reset(div_4);
	$.reset(div_1);
	$.reset(div);
	$.template_effect(($0) => button_2.disabled = $0, [() => !$.get(configText).trim()]);

	$.bind_value(
		textarea,
		function get() {
			return $.get(configText);
		},
		function set($$value) {
			$.set(configText, $$value);
		}
	);

	$.append($$anchor, div);

	return $.pop($$exports);
}

$.delegate(['click', 'keydown']);