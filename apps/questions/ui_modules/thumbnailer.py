import datetime
import os
from time import mktime
import tornado.web
import settings
import json
from tornado_utils.thumbnailer import get_thumbnail

class QuestionImageThumbnailMixin:

    def make_thumbnail(self, question_image, (max_width, max_height)):
        timestamp = int(mktime(question_image.modify_date.timetuple()))
        image = question_image.fs.get_last_version('original')
        if image.content_type == 'image/png':
            ext = '.png'
        elif image.content_type == 'image/jpeg':
            ext = '.jpg'
        #elif image.content_type == 'image/gif':
        #   ext = '.gif'
        else:
            raise ValueError("Unrecognized content_type %r" % image.content_type)
        path = (datetime.datetime.now()
                .strftime('%Y %m %d')
                .split())
        path.append('%s-%s-%s-%s%s' % (question_image._id,
                                       max_width, max_height,
                                       timestamp,
                                       ext))
        path.insert(0, settings.THUMBNAIL_DIRECTORY)
        path = os.path.join(*path)
        (width, height) = get_thumbnail(path, image.read(), (max_width, max_height))
        return path.replace(settings.ROOT, ''), (width, height)


class ShowQuestionImageThumbnail(tornado.web.UIModule,
                                 QuestionImageThumbnailMixin):
    def render(self, question_image, (max_width, max_height), alt="",
               return_json=False, return_args=False,
               **kwargs):
        uri, (width, height) = self.make_thumbnail(question_image,
                                                   (max_width, max_height))
        url = self.handler.static_url(uri.replace('/static/',''))
        args = {'src': url, 'width': width, 'height': height, 'alt': alt}
        if (not question_image.render_attributes
          or kwargs.get('save_render_attributes', False)):
            question_image.render_attributes = args
            question_image.save()
        if return_args:
            return args
        args.update(kwargs)
        if return_json:
            return json.dumps(args)
        tag = ['<img']
        for key, value in args.items():
            tag.append('%s="%s"' % (key, value))
        tag.append('>')
        return ' '.join(tag)

#class ShowQuestionImageThumbnailJSON(ShowQuestionImageThumbnail):
#    def render(self, *args, **kwargs):
#        kwargs['return_json'] = True
#        return super(ShowQuestionImageThumbnailJSON, self).render(*args, **kwargs)

class GetQuestionImageThumbnailSrc(ShowQuestionImageThumbnail):
    def render(self, *args, **kwargs):
        attrs = (super(GetQuestionImageThumbnailSrc, self)
                       .render(*args, return_args=True, **kwargs))
        return attrs['src']
