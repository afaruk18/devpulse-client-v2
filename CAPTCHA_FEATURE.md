# Captcha Feature

This document describes the captcha functionality that has been integrated into the DevPulse client core.

## Overview

The captcha feature presents periodic math challenges to users to verify human activity. It replaces the original CSV logging approach with an event-driven system that integrates seamlessly with the existing DevPulse architecture.

## Features

- **Async Operation**: Runs in a separate thread to avoid blocking other functionality
- **Event Integration**: Sends captcha events to the EventStore instead of logging to CSV
- **Configurable**: Interval and timeout settings can be configured
- **Non-blocking**: Uses zenity dialogs for user interaction
- **Error Handling**: Graceful handling of dialog errors and user cancellations

## Configuration

The captcha feature can be configured through the tracker settings:

```python
# In tracker_config.py
CAPTCHA_INTERVAL: int = Field(10, description="seconds between captcha challenges (0 = disabled)")
CAPTCHA_INFO_TIMEOUT: int = Field(3, description="seconds to show captcha success dialog")
```

- `CAPTCHA_INTERVAL`: How often to present captcha challenges (0 disables the feature)
- `CAPTCHA_INFO_TIMEOUT`: How long to show the success dialog

## Event Structure

Captcha events are logged to the EventStore with the following structure:

```python
{
    "username": "user",
    "timestamp": datetime,
    "event": "captcha_challenge",
    "expression": "5 + 3",
    "user_answer": 8,
    "correct_answer": 8,
    "is_correct": True
}
```

## Integration

The CaptchaTask is automatically integrated into the ActivityTracker when enabled:

```python
# In event_client.py
if tracker_settings.CAPTCHA_INTERVAL > 0:
    self.tasks.append(
        CaptchaTask(
            interval=tracker_settings.CAPTCHA_INTERVAL,
            info_timeout=tracker_settings.CAPTCHA_INFO_TIMEOUT
        )
    )
```

## Usage

The captcha feature is automatically enabled when `CAPTCHA_INTERVAL > 0`. Users will see math challenge dialogs at the configured interval.

### Example Math Challenges

- Simple addition: "5 + 3 = ?"
- Simple subtraction: "10 - 4 = ?"
- Numbers range from 1-20 for easy mental calculation

### User Experience

1. **Challenge Dialog**: A zenity entry dialog appears with a math problem
2. **User Input**: User enters their answer and clicks OK
3. **Validation**: System checks if the answer is correct
4. **Feedback**: Success or error dialog is shown
5. **Logging**: Event is logged to the EventStore for later transmission

## Technical Implementation

### Key Components

1. **CaptchaTask**: Main task class that manages the captcha lifecycle
2. **Threading**: Uses separate threads to avoid blocking the main application
3. **EventStore Integration**: Logs events using the existing event system
4. **Zenity Integration**: Uses zenity for cross-platform dialog support

### Thread Safety

The captcha task runs in a daemon thread to ensure it doesn't prevent the application from shutting down properly. The EventStore operations are thread-safe.

### Error Handling

- Dialog errors are caught and ignored to prevent crashes
- User cancellations are handled gracefully
- Invalid input shows an error dialog and allows retry
- Network/transmission errors don't affect the captcha functionality

## Testing

Use the provided test scripts to verify functionality:

```bash
# Basic functionality test
python3 test_captcha.py

# Full integration test (triggers actual dialogs)
python3 test_captcha_full.py
```

## Dependencies

- `zenity`: Required for dialog functionality (Linux/Unix)
- `subprocess`: For running zenity commands
- `threading`: For non-blocking operation
- `random`: For generating math problems

## Future Enhancements

Potential improvements could include:

- Different types of challenges (not just math)
- Difficulty levels
- Custom challenge generation
- Alternative dialog systems for different platforms
- Analytics on user performance

## Migration from Original

The original implementation logged to CSV files. This new implementation:

1. ✅ Integrates with the event system
2. ✅ Runs asynchronously 
3. ✅ Sends events to the queue
4. ✅ Configurable through settings
5. ✅ Non-blocking operation
6. ✅ Better error handling