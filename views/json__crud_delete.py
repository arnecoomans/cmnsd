class CrudDelete:
  def crud__delete(self):
    ''' Delete an object instance '''
    if not self.obj:
      raise ValueError('No object instance provided for deletion')
    # self.obj.delete()
    self.messages.add(f'Object {self.obj} deleted', 'success')
    return {'deleted': True}
  