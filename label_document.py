from PIL import Image
from pdf2image import convert_from_bytes
from streamlit_drawable_canvas import st_canvas
import streamlit as st
from ocr_crop import ocr_crop


def load_file(file):
    if file.type == "application/pdf":
        return convert_from_bytes(file.getvalue())[0]
    return Image.open(file)


def labelling(uploaded_files):
    selected_file = st.selectbox("Select file", [f.name for f in uploaded_files])
    file          = next(f for f in uploaded_files if f.name == selected_file)
    image         = load_file(file)

    display_w = image.width  // 2
    display_h = image.height // 2
    scale_x   = image.width  / display_w
    scale_y   = image.height / display_h

    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.3)",
        stroke_width=2,
        background_image=image,
        height=display_h,
        width=display_w,
        drawing_mode="rect",
        key=selected_file
    )

    field = st.selectbox("Field", st.session_state.fields)

    if st.button("Save Annotation"):
        objects = (canvas_result.json_data or {}).get("objects", [])
        if not objects:
            st.warning("Draw a box first")
        else:
            obj  = objects[-1]
            bbox = {
                "left":   obj["left"],
                "top":    obj["top"],
                "width":  obj["width"],
                "height": obj["height"]
            }

            with st.spinner("Running OCR on crop..."):
                ocr_text = ocr_crop(image, bbox, scale_x, scale_y)

            st.session_state.labels.setdefault(selected_file, {}).setdefault(field, []).append({
                **bbox,
                "scale_x":  scale_x,
                "scale_y":  scale_y,
                "img_width":  image.width,   # ← store original image dimensions
                "img_height": image.height,
                "ocr_text": ocr_text
            })
            st.success(f"✅ Saved '{field}' → \"{ocr_text}\"")

    st.json(st.session_state.labels)