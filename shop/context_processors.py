from .models import BrandingSettings

def is_color_dark(hex_color):
    """
    Determines if a color is dark based on its luminance.
    Returns True if dark, False if light.
    """
    hex_color = hex_color.lstrip('#')

    
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])

    try:
        r, g, b = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        luminance = (0.299 * r + 0.587 * g + 0.114 * b)
        return luminance < 128  
    except:
        return True  

def branding_context(request):
    settings = BrandingSettings.objects.first()
    theme_class = 'navbar-dark'  

    if settings and settings.primary_color:
        if is_color_dark(settings.primary_color):
            theme_class = 'navbar-dark'
        else:
            theme_class = 'navbar-light'

    return {
        'branding': settings,
        'navbar_theme': theme_class
    }
