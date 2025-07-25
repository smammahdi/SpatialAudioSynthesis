import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  LinearProgress,
  Alert,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction
} from '@mui/material';
import {
  CloudUpload,
  Delete,
  AudioFile
} from '@mui/icons-material';
import { WebSocketService } from '../services/WebSocketService';
import { AudioSource } from '../services/AudioSourceManager';

interface AudioUploadDialogProps {
  open: boolean;
  onClose: () => void;
  onAudioUploaded: (source: AudioSource) => void;
  customSources: AudioSource[];
  onDeleteSource: (id: string) => void;
  websocketService: WebSocketService;
}

export const AudioUploadDialog: React.FC<AudioUploadDialogProps> = ({
  open,
  onClose,
  onAudioUploaded,
  customSources,
  onDeleteSource,
  websocketService
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [audioName, setAudioName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      const validTypes = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4'];
      if (!validTypes.includes(file.type)) {
        setError('Please select a valid audio file (MP3, WAV, OGG, MP4)');
        return;
      }
      
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB');
        return;
      }
      
      setSelectedFile(file);
      setError(null);
      
      // Auto-generate name from filename
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '');
      setAudioName(nameWithoutExt);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !audioName.trim()) {
      setError('Please select a file and enter a name');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const response = await websocketService.uploadAudio(selectedFile, audioName.trim());
      
      if (response.success) {
        const newSource: AudioSource = {
          id: response.id,
          name: response.name,
          type: 'custom',
          filename: response.filename,
          category: 'Custom Audio'
        };
        
        onAudioUploaded(newSource);
        
        // Reset form
        setSelectedFile(null);
        setAudioName('');
        setError(null);
        
        console.log('Audio uploaded successfully:', response.name);
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setError('Failed to upload audio file. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (!uploading) {
      setSelectedFile(null);
      setAudioName('');
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <CloudUpload />
          Manage Audio Files
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box display="flex" flexDirection="column" gap={3}>
          {/* Upload Section */}
          <Box>
            <Typography variant="h6" gutterBottom>
              Upload New Audio
            </Typography>
            
            <Box display="flex" flexDirection="column" gap={2}>
              <input
                accept="audio/*"
                style={{ display: 'none' }}
                id="audio-file-input"
                type="file"
                onChange={handleFileSelect}
                disabled={uploading}
              />
              <label htmlFor="audio-file-input">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<AudioFile />}
                  disabled={uploading}
                  sx={{ width: '100%' }}
                >
                  {selectedFile ? selectedFile.name : 'Select Audio File'}
                </Button>
              </label>
              
              {selectedFile && (
                <TextField
                  label="Audio Name"
                  value={audioName}
                  onChange={(e) => setAudioName(e.target.value)}
                  fullWidth
                  disabled={uploading}
                  placeholder="Enter a name for this audio"
                />
              )}
              
              {error && (
                <Alert severity="error">{error}</Alert>
              )}
              
              {uploading && (
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Uploading audio file...
                  </Typography>
                  <LinearProgress />
                </Box>
              )}
            </Box>
          </Box>
          
          {/* Custom Audio List */}
          {customSources.length > 0 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Your Custom Audio Files
              </Typography>
              
              <List>
                {customSources.map((source) => (
                  <ListItem key={source.id}>
                    <ListItemText
                      primary={source.name}
                      secondary={`Custom audio • ${source.filename}`}
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => onDeleteSource(source.id)}
                        disabled={uploading}
                      >
                        <Delete />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          Close
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={!selectedFile || !audioName.trim() || uploading}
          startIcon={<CloudUpload />}
        >
          Upload Audio
        </Button>
      </DialogActions>
    </Dialog>
  );
};
