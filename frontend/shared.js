// Shared utility functions for Hevy API Dashboard

// Show sync result in a consistent format
function showSyncResult(result) {
  const exerciseSync = result.exercise_sync || {};
  alert(`Sync completed!\n\nWorkouts:\nWorkouts seen: ${result.workouts_seen ?? 'N/A'}\nWorkouts updated: ${result.workouts_upserted ?? 'N/A'}\nSets inserted: ${result.sets_inserted ?? 'N/A'}\nWorkouts deleted: ${result.workouts_deleted ?? 'N/A'}\n\nExercise Templates:\nExercises imported: ${exerciseSync.imported_count ?? 'N/A'}\nTotal templates: ${exerciseSync.total_templates ?? 'N/A'}\nStatus: ${exerciseSync.status ?? 'N/A'}`);
}

// Common API call utility with error handling
async function apiCall(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

// Common error handler for async functions
function handleAsyncError(error, context = 'Operation') {
  alert(`${context} failed: ${error.message}`);
}

// Common sync button functionality
function setupSyncButton() {
  document.getElementById('syncBtn')?.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!confirm('Starting sync with Hevy API (workouts + exercise templates)')) return;
    
    const syncBtn = document.getElementById('syncBtn');
    const originalText = syncBtn.textContent;
    
    // Show loading state
    syncBtn.disabled = true;
    syncBtn.innerHTML = '⏳ Syncing...';
    syncBtn.style.opacity = '0.7';
    
    try {
      const res = await fetch('/sync/hevy?page=1&page_size=10', { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        showSyncResult(result);
      } else {
        alert('Sync failed.');
      }
    } catch (err) {
      alert('Sync error: ' + err.message);
    } finally {
      // Restore button state
      syncBtn.disabled = false;
      syncBtn.textContent = originalText;
      syncBtn.style.opacity = '1';
    }
  });
}

// Format date for display
function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString();
}

// Format date and time for display
function formatDateTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString();
}
