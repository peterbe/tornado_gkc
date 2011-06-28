import datetime
import os
import tornado.web
import settings
from utils.thumbnailer import get_thumbnail

class QuestionImageThumbnailMixin:

    def make_thumbnail(self, question_image, (max_width, max_height)):
        image = question_image.fs.get_last_version('original')
        if image.content_type == 'image/png':
            ext = '.png'
        elif image.content_type == 'image/jpeg':
            ext = '.jpg'
        else:
            raise ValueError("Unrecognized content_type %r" % image.content_type)
        path = (datetime.datetime.now()
                .strftime('%Y %m %d')
                .split())
        path.append('%s-%s-%s%s' % (question_image._id,
                                     max_width, max_height,
                                     ext))
        path.insert(0, settings.THUMBNAIL_DIRECTORY)
        path = os.path.join(*path)
        (width, height) = get_thumbnail(path, image.read(), (max_width, max_height))
        return path.replace(settings.ROOT, ''), (width, height)

class ShowQuestionImageThumbnail(tornado.web.UIModule,
                                 QuestionImageThumbnailMixin):
    def render(self, question_image, (max_width, max_height), alt="", **kwargs):
        uri, (width, height) = self.make_thumbnail(question_image,
                                                   (max_width, max_height))
        url = self.handler.static_url(uri.replace('/static/',''))
        args = {'src': url, 'width': width, 'height': height, 'alt': alt}
        args.update(kwargs)
        tag = ['<img']
        for key, value in args.items():
            tag.append('%s="%s"' % (key, value))
        tag.append('>')
        return ' '.join(tag)
