from django import forms


class UploadForm(forms.Form):
    image = forms.ImageField(required=False)
    image_url = forms.URLField(required=False, label="图片 URL")

    topk = forms.IntegerField(required=False, min_value=1, max_value=200, initial=50)
    threshold = forms.FloatField(required=False, min_value=0.0, max_value=1.0, initial=0.0)

    def clean(self):
        cleaned = super().clean()
        image = cleaned.get("image")
        image_url = cleaned.get("image_url")
        if not image and not image_url:
            raise forms.ValidationError("请上传图片")
        return cleaned
