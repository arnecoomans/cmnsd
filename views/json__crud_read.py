import traceback

class CrudRead:
  ''' CRUD Read action
  '''
  def crud__read(self):
    # Build Payload
    payload = {}
    try:
      if hasattr(self.obj, 'fields') and self.obj.fields:
        # If fields are detected, add the rendered fields to the payload
        for field in self.obj.fields:
          payload[field] = self.render_field(field)
      elif self.obj:
        # If only object is detected, add the rendered object to the payload
        payload[self.model.name] = self.render_obj(self.obj)
      elif self.model:
        # If only model is detected, add the rendered model to the payload
        payload[self.model.name] = self.render_model(self.model)
    except Exception as e:
      # Log the exception trackback to the console or log when
      # DEBUG is True in settings.py
      traceback.print_exc()
      self.messages.add(str(e), 'error')
      self.status = 400
      return {'error': str(e)}
    return payload
