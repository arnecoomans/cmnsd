from django.conf import settings

class Messages:
  def __init__(self):
    self.__messages = []
    self.__is_staff = False

  def set_is_staff(self, is_staff):
    self.__is_staff = is_staff

  def add(self, message, level='info'):
    """
    Add a message. If a message with the same level and message exists,
    increment the count by 1.

    Args:
        level (str): The level of the message (e.g., 'info', 'error').
        message (str): The message content.
    """
    for entry in self.__messages:
      if entry['level'].lower() == level and entry['message'] == message:
        entry['count'] += 1
        return
    # If no matching entry is found, add a new one
    self.__messages.append({'level': level.lower(), 'message': str(message), 'count': 1})

  def get(self):
    """
    Retrieve all messages, excluding messages with level='debug' unless debug is True.

    Args:
        debug (bool): If True, include messages with level='debug'.

    Returns:
        list of dict: The filtered list of messages.
    """
    if getattr(settings, 'DEBUG', False) and self.__is_staff:
      messages = self.__messages
    else:
      messages = self.exclude(level='debug')
    # Translate Level 'Debug' to 'Info' and prepend message with 'DEBUG: '
    for msg in messages:
      if msg['level'] == 'debug':
        msg['level'] = 'secondary'
        msg['message'] = 'DEBUG: ' + msg['message']
      elif msg['level'] == 'error':
        msg['level'] = 'danger'
    return messages

  def exclude(self, level=None, message=None):
    """
    Exclude messages based on level or message.

    Args:
        level (str, optional): The level to exclude (e.g., 'debug').
        message (str, optional): The message content to exclude.

    Returns:
        list of dict: The filtered list of messages.
    """
    filtered_messages = self.__messages
    if level:
      filtered_messages = [msg for msg in filtered_messages if msg['level'] != level]
    if message:
      filtered_messages = [msg for msg in filtered_messages if msg['message'] != message]
    return filtered_messages
  
  def __str__(self):
    return self.get()
  
class MessageUtil:
  def __init__(self):
    self.messages = Messages()
    super().__init__()

  def dispatch(self, request, *args, **kwargs):
    return super().dispatch(request, *args, **kwargs)
  
  def setup(self, request, *args, **kwargs):
    # Set the is_staff attribute based on the request user
    if hasattr(request, 'user'):
      self.messages.set_is_staff(request.user.is_staff)
    # Call the setup method of the superclass if it exists
    if hasattr(super(), 'setup'):
      super().setup(request, *args, **kwargs)