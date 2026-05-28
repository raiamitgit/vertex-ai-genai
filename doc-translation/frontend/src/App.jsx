import { useState, useRef } from 'react';
import { UploadCloud, File as FileIcon, X, CheckCircle, Download, Loader2 } from 'lucide-react';
import './index.css';

const SUPPORTED_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation'
];

function App() {
  const [file, setFile] = useState(null);
  const [sourceLang, setSourceLang] = useState('en');
  const [targetLang, setTargetLang] = useState('ja');
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [resultFileName, setResultFileName] = useState('');
  const [isLargeFile, setIsLargeFile] = useState(false);

  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const validateAndSetFile = (selectedFile) => {
    if (selectedFile) {
      if (!SUPPORTED_TYPES.includes(selectedFile.type)) {
        setError("Please upload a supported file type (.pdf, .docx, .doc, .pptx, .ppt)");
        setFile(null);
        setIsLargeFile(false);
        return;
      }

      const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB in bytes
      if (selectedFile.size > MAX_FILE_SIZE) {
        setIsLargeFile(true);
      } else {
        setIsLargeFile(false);
      }

      setFile(selectedFile);
      setError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleTranslate = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_language', sourceLang);
    formData.append('target_language', targetLang);

    try {
      const response = await fetch('http://localhost:8000/api/translate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Server responded with ${response.status}`);
      }

      // Get filename from header if possible
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `translated_${file.name}`;
      if (contentDisposition && contentDisposition.indexOf('filename=') !== -1) {
        const regex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
        const matches = regex.exec(contentDisposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      setResultUrl(url);
      setResultFileName(filename);

    } catch (err) {
      setError(err.message || 'An error occurred during translation.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setResultUrl(null);
    setResultFileName('');
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <>
      <div className="background-glow"></div>
      <div className="app-container">
        <header className="header">
          <h1>LuminaDocs</h1>
          <p>Select your languages and upload a file to begin.</p>
        </header>

        <main className="main-card">
          {error && <div className="error-msg">{error}</div>}

          {!resultUrl ? (
            <>
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                onChange={handleFileChange}
                accept=".pdf,.doc,.docx,.ppt,.pptx"
              />

              {!file ? (
                <div
                  className={`dropzone ${isDragging ? 'active' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <UploadCloud className={`drop-icon ${isDragging ? 'active' : ''}`} />
                  <div>
                    <div className="drop-title">Drag & Drop File Here</div>
                    <div className="drop-subtitle">Or click to browse computer</div>
                  </div>
                  <div className="drop-subtitle" style={{ fontSize: '12px' }}>
                    Supports .pdf, .docx, .pptx
                  </div>
                </div>
              ) : (
                <div className="file-info">
                  <FileIcon className="file-icon" />
                  <span className="file-name">{file.name}</span>
                  <button className="remove-btn" onClick={(e) => { e.stopPropagation(); resetForm(); }}>
                    <X size={18} />
                  </button>
                </div>
              )}

              <div className="controls">
                <div className="control-group">
                  <label>Source Language</label>
                  <select
                    className="select-box"
                    value={sourceLang}
                    onChange={(e) => setSourceLang(e.target.value)}
                    disabled={isLoading}
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="es">Spanish</option>
                  </select>
                </div>
                <div className="control-group">
                  <label>Target Language</label>
                  <select
                    className="select-box"
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    disabled={isLoading}
                  >
                    <option value="ja">Japanese</option>
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                  </select>
                </div>
              </div>

              <button
                className="action-btn"
                onClick={handleTranslate}
                disabled={!file || isLoading}
              >
                {isLoading ? (
                  <>
                    <div className="loader"></div>
                    {isLargeFile ? 'Translating Large File (ETA: 1-3 min)...' : 'Translating...'}
                  </>
                ) : (
                  'Translate Document'
                )}
              </button>
            </>
          ) : (
            <div className="success-state">
              <CheckCircle className="success-icon" />
              <h2 className="success-title">Translation Complete</h2>
              <p style={{ color: '#86868b', marginBottom: '30px' }}>Your document has been successfully translated.</p>

              <a
                href={resultUrl}
                download={resultFileName || 'translated_document'}
                className="action-btn"
                style={{ textDecoration: 'none', display: 'flex' }}
              >
                <Download size={20} />
                Download Translated File
              </a>

              <button className="reset-btn" onClick={resetForm}>
                Translate Another Document
              </button>
            </div>
          )}
        </main>
      </div>
    </>
  );
}

export default App;
