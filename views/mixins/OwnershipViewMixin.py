class OwnershipViewMixin:
  """
  Assigns the current user as owner when a new object is created through
  a ModelForm-based view (e.g. CreateView). Only sets it on creation - an
  existing owner is never overwritten on update. Composing view is
  responsible for requiring authentication (e.g. LoginRequiredMixin).
  """

  def form_valid(self, form):
    if form.instance.pk is None:
      form.instance.user = self.request.user
    return super().form_valid(form)
