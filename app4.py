import streamlit as st
import os
import zipfile
import tempfile
import shutil
from PIL import Image
from io import BytesIO
import time
import base64

# Set page config for better appearance
st.set_page_config(
    page_title="Smart Image Compressor",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* ... (previous CSS styles remain unchanged) ... */
</style>
""", unsafe_allow_html=True)

def compress_image(img, target_kb):
    quality = 90
    step = 5
    while quality > 10:
        buffer = BytesIO()
        img.save(buffer, format="WEBP", quality=quality)
        size_kb = buffer.tell() / 1024
        if size_kb <= target_kb:
            break
        quality -= step
    buffer.seek(0)
    return buffer.getvalue(), size_kb, quality

def create_download_zip(compressed_files):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, data, _, _ in compressed_files:
            zip_file.writestr(f"compressed_{filename.split('.')[0]}.webp", data)
    return zip_buffer.getvalue()

def main():
    st.markdown('<h1 class="main-header">Smart Image Compressor</h1>', unsafe_allow_html=True)
    
    # Initialize session state for compressed files
    if 'compressed_files' not in st.session_state:
        st.session_state.compressed_files = None
    
    with st.expander("ℹ️ About this app", expanded=False):
        st.markdown("""
        <div class="info-text">
        This app compresses images to a target file size while maintaining the best possible quality.
        
        <b>Features:</b>
        <ul>
            <li>Upload individual files or a ZIP archive</li>
            <li>Set your target file size in KB</li>
            <li>Download compressed images individually or as a ZIP file</li>
            <li>Automatic quality adjustment to meet target size</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3><span class="step-number">1</span> Upload Images</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        selection_type = st.radio(
            "Select input type:", 
            ["Files", "ZIP"],
            index=1,  # Set default to "ZIP"
            horizontal=True,
            help="Choose whether to upload individual files or a ZIP archive containing multiple images"
        )
        
        if selection_type == "Files":
            uploaded_files = st.file_uploader(
                "Choose image files", 
                accept_multiple_files=True, 
                type=["png", "jpg", "jpeg", "webp"]
            )
            file_count = len(uploaded_files) if uploaded_files else 0
        else:
            uploaded_zip = st.file_uploader("Choose a ZIP file", type="zip")
            file_count = "multiple" if uploaded_zip else 0
        
        if file_count:
            st.success(f"{'Multiple' if file_count == 'multiple' else file_count} files ready for compression")
    
    with col2:
        st.markdown('<h3><span class="step-number">2</span> Set Target Size</h3>', unsafe_allow_html=True)
        target_kb = st.slider(
            "Target Size (KB):", 
            min_value=10, 
            max_value=500, 
            value=45,
            help="Maximum file size for each compressed image"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    compress_button = st.button("🚀 Compress Images", use_container_width=True, type="primary")
    
    if compress_button:
        if (selection_type == "Files" and uploaded_files) or (selection_type == "ZIP" and uploaded_zip):
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown('<h3><span class="step-number">3</span> Processing</h3>', unsafe_allow_html=True)
            
            with st.spinner("Working on your images..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                if selection_type == "Files" and uploaded_files:
                    st.session_state.compressed_files = process_files(uploaded_files, target_kb, progress_bar, status_text)
                else:
                    st.session_state.compressed_files = process_zip(uploaded_zip, target_kb, progress_bar, status_text)
                
                progress_bar.progress(100)
                status_text.success("✅ Compression complete!")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("Please upload files or a ZIP archive before compressing.")
    
    if st.session_state.compressed_files:
        display_results(st.session_state.compressed_files)

def process_files(uploaded_files, target_kb, progress_bar, status_text):
    compressed_files = []
    total_files = len(uploaded_files)
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing file {i+1}/{total_files}: {uploaded_file.name}")
        progress_bar.progress((i) / total_files)
        
        time.sleep(0.1)
        
        try:
            img = Image.open(uploaded_file)
            original_size = uploaded_file.size / 1024  # KB
            
            if img.mode in ('RGBA', 'LA'):
                img = img.convert('RGB')
                
            compressed_data, final_size, quality = compress_image(img, target_kb)
            compressed_files.append((uploaded_file.name, compressed_data, original_size, final_size))
            
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")
    
    return compressed_files

def process_zip(uploaded_zip, target_kb, progress_bar, status_text):
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "uploaded.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.getvalue())
        
        status_text.text("Extracting ZIP file...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        image_files = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    image_files.append((file, os.path.join(root, file)))
        
        total_files = len(image_files)
        status_text.text(f"Found {total_files} images in ZIP file")
        
        compressed_files = []
        for i, (filename, file_path) in enumerate(image_files):
            status_text.text(f"Processing file {i+1}/{total_files}: {filename}")
            progress_bar.progress((i) / total_files)
            
            time.sleep(0.1)
            
            try:
                img = Image.open(file_path)
                original_size = os.path.getsize(file_path) / 1024  # KB
                
                if img.mode in ('RGBA', 'LA'):
                    img = img.convert('RGB')
                    
                compressed_data, final_size, quality = compress_image(img, target_kb)
                compressed_files.append((filename, compressed_data, original_size, final_size))
                
            except Exception as e:
                st.error(f"Error processing {filename}: {e}")
    
    return compressed_files

def display_results(compressed_files):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3><span class="step-number">4</span> Download Results</h3>', unsafe_allow_html=True)
    
    total_original = sum(original_size for _, _, original_size, _ in compressed_files)
    total_compressed = sum(final_size for _, _, _, final_size in compressed_files)
    savings = ((total_original - total_compressed) / total_original * 100) if total_original > 0 else 0
    
    st.markdown(f"""
    <div class="success-box">
        <h4>Compression Summary</h4>
        <ul>
            <li><b>Files compressed:</b> {len(compressed_files)}</li>
            <li><b>Original size:</b> {total_original:.1f} KB ({total_original/1024:.2f} MB)</li>
            <li><b>Compressed size:</b> {total_compressed:.1f} KB ({total_compressed/1024:.2f} MB)</li>
            <li><b>Space saved:</b> {savings:.1f}% ({(total_original-total_compressed)/1024:.2f} MB)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    zip_data = create_download_zip(compressed_files)
    st.download_button(
        label="📦 Download All as ZIP",
        data=zip_data,
        file_name="compressed_images.zip",
        mime="application/zip",
        use_container_width=True
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    view_mode = st.radio(
        "View files as:",
        ["Grid View", "List View"],  # Remove "ZIP" option
        horizontal=True,
        index=0,
    )
    
    if view_mode != "ZIP":
        st.write("### Individual Files")
    
        if view_mode == "Grid View":
            num_cols = 3
            file_columns = st.columns(num_cols)
            
            for i, (filename, compressed_data, original_size, final_size) in enumerate(compressed_files):
                col = file_columns[i % num_cols]
                with col:
                    reduction = ((original_size - final_size) / original_size * 100) if original_size > 0 else 0
                    st.markdown(f"""
                    <div class="file-card">
                        <p><strong>{filename}</strong></p>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Original: <b>{original_size:.1f} KB</b></span>
                            <span>➡️</span>
                            <span>Compressed: <b>{final_size:.1f} KB</b></span>
                        </div>
                        <div style="margin-top: 5px; height: 6px; background-color: #f3f4f6; border-radius: 9999px; overflow: hidden;">
                            <div style="width: {100-reduction:.1f}%; height: 100%; background-color: #10b981;"></div>
                        </div>
                        <div style="text-align: right; font-size: 0.9rem; margin-top: 3px;">
                            <b>{reduction:.1f}%</b> reduction
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.download_button(
                        label=f"⬇️ Download",
                        data=compressed_data,
                        file_name=f"compressed_{filename.split('.')[0]}.webp",
                        mime="image/webp",
                        use_container_width=True,
                        key=f"btn_{i}"
                    )
        else:
            for i, (filename, compressed_data, original_size, final_size) in enumerate(compressed_files):
                reduction = ((original_size - final_size) / original_size * 100) if original_size > 0 else 0
                
                cols = st.columns([3, 2, 2, 2, 1])
                with cols[0]:
                    st.markdown(f"<b>{filename}</b>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"Original: <b>{original_size:.1f} KB</b>", unsafe_allow_html=True)
                with cols[2]:
                    st.markdown(f"Compressed: <b>{final_size:.1f} KB</b>", unsafe_allow_html=True)
                with cols[3]:
                    st.markdown(f"Reduced: <b>{reduction:.1f}%</b>", unsafe_allow_html=True)
                with cols[4]:
                    st.download_button(
                        label="⬇️",
                        data=compressed_data,
                        file_name=f"compressed_{filename.split('.')[0]}.webp",
                        mime="image/webp",
                        key=f"list_btn_{i}"
                    )
                
                if i < len(compressed_files) - 1:
                    st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
