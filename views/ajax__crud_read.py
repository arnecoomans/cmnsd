import traceback

class CrudRead:
  ''' CRUD Read action
  '''
  def crud__read(self):
    # Build Payload
    payload = {}
    format = self.get_value_from_request('format', silent=True, default='html')
    try:
      if hasattr(self.obj, 'fields') and self.obj.fields or \
         hasattr(self.obj, 'functions') and self.obj.functions:
        if hasattr(self.obj, 'fields') and self.obj.fields:
          # If fields are detected, add the rendered fields to the payload
          for field in self.obj.fields:
            payload[field] = self.render_field(field, format=format)
        if hasattr(self.obj, 'functions') and self.obj.functions:
          # If functions are detected, add the rendered functions to the payload
          for function in self.obj.functions:
            payload[function] = self.render_field(function, format=format)
      elif self.obj.is_found():
        # If only object is detected, add the rendered object to the payload
        payload[self.model.name] = self.render_obj(self.obj, format=format)
      elif self.model:
        # If only model is detected, add the rendered model to the payload
        payload[self.model.name] = self.render_model(self.model, format=format)
    except Exception as e:
      # Log the exception trackback to the console or log when
      # DEBUG is True in settings.py
      traceback.print_exc()
      self.messages.add(str(e), 'error')
      self.status = 400
      return {'error': str(e)}
    return payload
