import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
	name: "Comfy.ArchiveImageLoader",
	async beforeRegisterNodeDef(nodeType, nodeData) {
		// Target the new node by its class name
		if (nodeData.name === "ArchiveImageLoader") {
			const onNodeCreated = nodeType.prototype.onNodeCreated;
			nodeType.prototype.onNodeCreated = function () {
				onNodeCreated?.apply(this, arguments);

				// Shared function to upload the file to the temp folder
				const uploadFile = async (file) => {
					try {
						const body = new FormData();
						body.append("image", file);
						body.append("overwrite", "true");
						body.append("type", "temp");
						const resp = await api.fetchApi("/upload/image", {
							method: "POST",
							body,
						});

						if (resp.status === 200) {
							const data = await resp.json();
							// Set the hidden widget's value to the uploaded file's name
							const path = data.name; // Only the filename is needed
							const textWidget = this.widgets.find((w) => w.name === "archive_file");
							if (textWidget) {
								textWidget.value = path;
							}
						} else {
							alert(`Upload Error: ${resp.status} - ${resp.statusText}`);
						}
					} catch (error) {
						console.error("Upload failed:", error);
						alert(`Upload failed: ${error}`);
					}
				};

				// Create the "Upload Archive" button
				this.addWidget("button", "upload_archive", "Upload Archive", () => {
					const inputEl = document.createElement("input");
					inputEl.type = "file";
					// Define accepted file types
					inputEl.accept = ".zip,.7z,.rar";
					document.body.appendChild(inputEl);

					inputEl.addEventListener("change", () => {
						if (inputEl.files.length > 0) {
							uploadFile(inputEl.files[0]);
						}
						inputEl.remove();
					});

					inputEl.style.display = "none";
					inputEl.click();
				});

				// Drag-and-drop event handling
				this.onDragOver = function(e) {
					if (e.dataTransfer?.types.includes("Files")) {
						e.preventDefault();
						return true;
					}
					return false;
				};

				this.onDragDrop = async function(e) {
					e.preventDefault();
					e.stopPropagation();

					let handled = false;
					for (const file of e.dataTransfer.files) {
						// Check for supported file extensions
						if (file.name.toLowerCase().endsWith(".zip") || file.name.toLowerCase().endsWith(".7z") || file.name.toLowerCase().endsWith(".rar")) {
							await uploadFile(file);
							handled = true;
							break; // Handle only the first valid file
						}
					}
					return handled;
				};
			};
		}
	},
});