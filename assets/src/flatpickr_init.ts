import flatpickr from "flatpickr";
import "flatpickr/dist/flatpickr.css";

function initFlatpickr(): void {
	document
		.querySelectorAll<HTMLInputElement>(".js-flatpickr")
		.forEach((el) => {
			flatpickr(el, {
				dateFormat: "Y-m-d",
				allowInput: true,
			});
		});
}

document.addEventListener("DOMContentLoaded", initFlatpickr);
