"""Universal file upload automation across all ATS platforms.

Handles three upload patterns:
1. Standard input[type='file'] (Greenhouse, Lever, LinkedIn, SmartRecruiters)
2. Drag-and-drop simulation via DataTransfer events (Workday)
3. Hidden file input reveal + send_keys (most platforms)

Also handles PDF vs DOCX format selection per platform.
"""

import os
from pathlib import Path
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.logger import log

# JavaScript to reveal all hidden file inputs on a page
REVEAL_FILE_INPUTS_JS = """
document.querySelectorAll('input[type="file"]').forEach(el => {
    el.style.display = 'block';
    el.style.visibility = 'visible';
    el.style.opacity = '1';
    el.style.position = 'relative';
    el.style.width = '200px';
    el.style.height = '30px';
    el.style.zIndex = '999999';
    el.removeAttribute('hidden');
});
"""

# JavaScript for drag-and-drop file simulation (Workday pattern)
# Based on florentbr/gist updated for Chrome 134+
JS_DROP_FILES = """
var k=arguments,d=k[0],g=k[1],c=k[2],m=d.ownerDocument||document;
for(var e=0;;){var f=d.getBoundingClientRect(),b=f.left+(g||(f.width/2)),
a=f.top+(c||(f.height/2)),h=m.elementFromPoint(b,a);
if(h&&d.contains(h)){break}if(++e>1){throw new Error('Element not interactable')}
d.scrollIntoView({behavior:'instant',block:'center',inline:'center'})}
var l=m.createElement('INPUT');l.setAttribute('type','file');l.setAttribute('multiple','');
l.setAttribute('style','position:fixed;z-index:2147483647;left:0;top:0;');
l.onchange=function(q){l.parentElement.removeChild(l);q.stopPropagation();
var r={constructor:DataTransfer,effectAllowed:'all',dropEffect:'none',
types:['Files'],files:l.files,setData:function(){},getData:function(){},
clearData:function(){},setDragImage:function(){}};
if(window.DataTransferItemList){r.items=Object.setPrototypeOf(
Array.prototype.map.call(l.files,function(x){return{constructor:DataTransferItem,
kind:'file',type:x.type,getAsFile:function(){return x},
getAsString:function(A){var z=new FileReader();z.onload=function(B){
A(B.target.result)};z.readAsText(x)},
webkitGetAsEntry:function(){return{constructor:FileSystemFileEntry,
name:x.name,fullPath:'/'+x.name,isFile:true,isDirectory:false,
file:function(A){A(x)}}}}}),{constructor:DataTransferItemList,
add:function(){},clear:function(){},remove:function(){}})};
['dragenter','dragover','drop'].forEach(function(v){
var w=m.createEvent('DragEvent');
w.initMouseEvent(v,true,true,m.defaultView,0,0,0,b,a,false,false,false,false,0,null);
Object.setPrototypeOf(w,null);w.dataTransfer=r;
Object.setPrototypeOf(w,DragEvent.prototype);h.dispatchEvent(w)})};
m.documentElement.appendChild(l);l.getBoundingClientRect();return l
"""

# Platforms that parse DOCX better than PDF
DOCX_PREFERRED_PLATFORMS = {"taleo", "icims", "adp"}

# Per-platform resume upload selectors
RESUME_SELECTORS = {
    "linkedin": "[id*='jobs-document-upload-file-input-upload-resume'], input.jobs-document-upload-file-input",
    "greenhouse": "input[type='file'][name='resume'], input[type='file'][id*='resume']",
    "lever": "input[name='resume'], input[type='file']",
    "workday": "input[data-automation-id='file-upload-input-ref']",
    "indeed": "input[type='file'][id*='resume'], input[type='file'][name*='resume']",
    "smartrecruiters": "input[type='file']",
    "icims": "input[type='file']",
    "default": "input[type='file']",
}

# Workday drag-drop region selector
WORKDAY_DROP_ZONE = "[data-automation-id='dragDropRegion']"

# Cover letter upload selectors
COVER_LETTER_SELECTORS = {
    "linkedin": "[id*='jobs-document-upload-file-input-upload-cover-letter']",
    "greenhouse": "input[type='file'][name='cover_letter'], textarea[name='cover_letter']",
    "lever": "textarea[name='comments']",
    "default": "input[type='file'][name*='cover'], input[type='file'][id*='cover']",
}


def get_resume_format(platform: str) -> str:
    """Determine preferred resume format for a platform."""
    if platform in DOCX_PREFERRED_PLATFORMS:
        return "docx"
    return "pdf"


def upload_file_standard(driver, selector: str, file_path: str) -> bool:
    """Upload a file via standard input[type='file'].

    Reveals hidden file inputs first, then uses send_keys.
    Works on ~70% of ATS platforms.
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        log.error(f"File not found: {abs_path}")
        return False

    try:
        # Reveal hidden file inputs
        driver.execute_script(REVEAL_FILE_INPUTS_JS)

        wait = WebDriverWait(driver, 10)
        file_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        file_input.send_keys(abs_path)
        log.info(f"File uploaded via standard input: {Path(abs_path).name}")
        return True

    except Exception as e:
        log.debug(f"Standard upload failed for '{selector}': {e}")
        return False


def upload_file_dragdrop(driver, drop_zone_selector: str, file_path: str) -> bool:
    """Upload a file via drag-and-drop simulation.

    Used for Workday and other platforms with drag-drop upload regions.
    Simulates DragEvent with DataTransfer object.
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        log.error(f"File not found: {abs_path}")
        return False

    try:
        drop_zone = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, drop_zone_selector))
        )

        # Execute the drag-drop simulation JS
        elm_input = driver.execute_script(JS_DROP_FILES, drop_zone, 0, 0)
        elm_input._execute(
            "sendKeysToElement",
            {"value": [abs_path], "text": abs_path},
        )
        log.info(f"File uploaded via drag-drop: {Path(abs_path).name}")
        return True

    except Exception as e:
        log.debug(f"Drag-drop upload failed: {e}")
        return False


def upload_resume(driver, platform: str, file_path: str) -> bool:
    """Upload resume using the best method for the given platform.

    Tries platform-specific selector first, then falls back to
    generic methods.
    """
    if not file_path or not os.path.exists(file_path):
        log.warning(f"Resume file not found: {file_path}")
        return False

    # Workday: try drag-drop first, fall back to hidden input
    if platform == "workday":
        if upload_file_dragdrop(driver, WORKDAY_DROP_ZONE, file_path):
            return True
        # Fall through to standard method

    # Get platform-specific selector
    selector = RESUME_SELECTORS.get(platform, RESUME_SELECTORS["default"])

    # Try standard upload
    if upload_file_standard(driver, selector, file_path):
        return True

    # Fallback: try any file input on the page
    if platform != "default":
        if upload_file_standard(driver, RESUME_SELECTORS["default"], file_path):
            return True

    log.warning(f"Resume upload failed on {platform}")
    return False


def upload_cover_letter(driver, platform: str, file_path: str) -> bool:
    """Upload cover letter file."""
    if not file_path or not os.path.exists(file_path):
        return False

    selector = COVER_LETTER_SELECTORS.get(platform, COVER_LETTER_SELECTORS["default"])

    # For textarea-based cover letters (Lever), read the file content
    if "textarea" in selector:
        try:
            el = driver.find_element(By.CSS_SELECTOR, selector)
            if el.tag_name == "textarea":
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                el.clear()
                el.send_keys(content)
                return True
        except Exception:
            pass

    return upload_file_standard(driver, selector, file_path)
