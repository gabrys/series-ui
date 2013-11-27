#!/usr/bin/env python
# encoding: utf-8

import du
import simplejson
import web

urls = (
    '/add/([^/]+)/([^/]+)/([^/]+)/([^/]+)', 'add',
    '/min_seeds/([^/]+)/([^/]+)/([^/]+)/([^/]+)', 'min_seeds',
    '/watched/([^/]+)/([^/]+)/([^/]+)', 'watched',
    '/remove/([^/]+)/([^/]+)/([^/]+)', 'remove',
    '/search/([^/]+)/([^/]+)/([^/]+)', 'search',
    '/download', 'download',
    '/', 'index',
)
app = web.application(urls, globals())

class index:
    def GET(self):
        return '' + tpl().replace('###DATA###', simplejson.dumps(du.get_tree()))

class watched:
    def GET(self, title, season, episode):
        du.remove_watched_entry(title, int(season), int(episode))
        raise web.seeother('/')

class remove:
    def GET(self, title, season, episode):
        du.remove_new_entry(title, int(season), int(episode))
        raise web.seeother('/')

class search:
    def GET(self, title, season, episode):
        raise web.seeother(du.tpb_search_url(title, int(season), int(episode)))

class add:
    def GET(self, title, season, episode, min_seeds):
        du.add_new_entry(title, season, episode, min_seeds)
        raise web.seeother('/')

class min_seeds:
    def GET(self, title, season, episode, min_seeds):
        du.update_min_seeds(title, season, episode, min_seeds)
        raise web.seeother('/')

class download:
    def GET(self):
        du.process_new()
        raise web.seeother('/')


def tpl():
    return """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Seriale</title>
<style>
html { background: #f5f5f5; }
body { font-family: Verdana; font-size: 13px; width: 800px; margin: 0 auto; background: #fff; box-shadow: 0 -10px 10px #aaa; padding: 0 10px 50px 30px; position: relative; }
h2 { font-family: Ubuntu; margin-top: 30px; }
a { text-decoration: none; color: #00f; }
a:hover { text-decoration: underline; }
a.download { position: absolute; top: 10px; right: 10px; }
.actions span, .status span { display: none; }
.new .status .new, .new .actions .new,
.fake .status .fake, .fake .actions .fake,
.queued .status .queued, .queued .actions .queued,
.verified .status .verified, .verified .actions .verified,
.downloaded .status .downloaded, .downloaded .actions .downloaded,
.ready .status .ready, .ready .actions .ready { display: inline; }
.episode-info { display: inline; }
li.new { opacity: 0.3; }
.status { display: inline; margin-left: 1em; padding: 4px 5px; border-radius: 4px; color: #fff; background: #666; font-size: 80%; text-transform: uppercase; font-weight: bold; }
.status a { color: #fff; }
.actions { display: inline; margin-left: 1em; }
.actions a { text-decoration: none; font-weight: bold; color: #222; margin-right: 10px; }
.verified .status { background: #a0a; }
.downloaded .status { background: #0a0; }
.ready .status { background: #0af; }
ul, li { list-style: none; padding: 0; margin: 0; }
li li { margin: 10px 0 10px 20px; list-style: square; }
#episodes { overflow: hidden; }
#episodes > li { float: left; width: 400px; list-style: none; margin: 0; }
#episodes > li:nth-child(2n+1) { clear: left; }
</style>
<script type="text/javascript" src="http://code.jquery.com/jquery-latest.min.js"></script>
<script type="text/javascript">

$(function() {
    $('a.download').click(function() {
        $(this).text('⟳ szukanie');
        if ($(this).attr('href') !== '#') {
            $.get($(this).attr('href'), function() {
                location.reload();
            });
            $(this).attr('href', '#');
        }
        return false;
    });
    $('input[type="text"]').each(function() {
        var empty = $(this).attr('value');
        $(this).focus(function() {
            if ($(this).val() === empty) {
                $(this).val('');
            }
        });
        $(this).blur(function() {
            if ($(this).val() === '') {
                $(this).val(empty);
            }
        });
    });
    $('form#new-episode').submit(function() {
        var $form = $(this);
        var title = $('[name="title"]', $form).val().replace(/ /g, '.');
        var season = parseInt($('[name="season"]', $form).val());
        var episode = parseInt($('[name="episode"]', $form).val());
        if (season >= 1 && episode >= 1) {
            location.href = '/add/' + title + '/' + season + '/' + episode + '/1000';
        }
        return false;
    });
    var $status = $('<div class="status">' +
        '<span class="new"><a href="#search">Oczekiwanie na odcinek</a></span>' +
        '<span class="fake"><a href="#search">Oczekiwanie na odcinek</a></span>' +
        '<span class="queued">Do ściągnięcia</span>' +
        '<span class="verified">Ściągane</span>' +
        '<span class="downloaded">Bez napisów</span>' +
        '<span class="ready">Z napisami</span>' +
    '</div>');
    var $actions = $('<div class="actions">' +
        '<span class="new"><a title="minimalna ilość seedów" href="#seeds">#</a><a title="usuń" href="#remove">×</a></span>' +
        '<span class="fake"><a title="minimalna ilość seedów" href="#seeds">#</a><a title="usuń" href="#remove">×</a></span>' +
        '<span class="queued"><a title="usuń" href="#remove">×</a></span>' +
        '<span class="downloaded"><a title="zaznacz jako objerzane" href="#watched">✔</a></span>' +
        '<span class="ready"><a title="zaznacz jako obejrzane" href="#watched">✔</a></span>' +
    '</div>');
    var $episodes = $('ul#episodes');
    var data = ###DATA###;
    for (var i in data) {
        var $li = $('<li/>');
        var $ul = $('<ul/>');
        var title = data[i][0];
        var episodes = data[i][1];

        $li.append($('<h2/>').text(title.replace(/\./g, ' ')));
        for (var j in episodes) {
                var $li2 = $('<li/>');
                var $info = $('<p class="episode-info"/>');
                var watched_link = 'watched/' + title + '/' + episodes[j][0] + '/' + episodes[j][1];
                var remove_link = 'remove/' + title + '/' + episodes[j][0] + '/' + episodes[j][1];
                var search_link = 'search/' + title + '/' + episodes[j][0] + '/' + episodes[j][1];
                var $episode_actions = $actions.clone();
                var $episode_status = $status.clone();

                $episode_actions.find('a[href="#watched"]').attr('href', watched_link);
                $episode_actions.find('a[href="#remove"]').attr('href', remove_link);
                $episode_status.find('a[href="#search"]').attr('href', search_link);

                $li2.addClass(episodes[j][2]);

                $info.text('Seria: ' + episodes[j][0] + ', odcinek ' + episodes[j][1]);
                $li2.append($info);

                $li2.append($episode_status);
                $li2.append($episode_actions);
                $ul.append($li2);

                (function(title, season, episode, min_seeds) {
                        $episode_actions.find('a[href="#seeds"]').click(function() {
                                var new_min_seeds = prompt('Minimalna ilość seedów', min_seeds);
                                if (new_min_seeds && new_min_seeds != min_seeds) {
                                        location.href = '/min_seeds/' + title + '/' + season + '/' + episode + '/' + new_min_seeds;
                                }
                                return false;
                        });
                }(title, episodes[j][0], episodes[j][1], episodes[j][3]));
        }
        $li.append($ul);
        $episodes.append($li);
    }
    var $actionWatched = $('.actions .downloaded:visible a, .actions .ready:visible a');
    $(document).on('keydown', function(e) {
        if (e.keyCode == 38 || e.keyCode == 40) {
            e.preventDefault();
            var currentIndex = $actionWatched.index($('a:focus'));
            if (e.keyCode == 38) {
                currentIndex -= 1;
            }
            if (e.keyCode == 40) {
                currentIndex += 1;
            }
            currentIndex %= $actionWatched.length;
            $actionWatched.eq(currentIndex).focus();
        }
    });
});

</script>
</head>

<body>
<a class="download" href="/download">⟳ szukaj oczekiwanych teraz</a>
<ul id="episodes">
</ul>
<form id="new-episode">
<h2>Dodaj</h2>
<input type="text" name="title" value="Tytuł">
<input type="text" name="season" value="Seria" size="2">
<input type="text" name="episode" value="Odcinek" size="2">
<button type="submit">Dodaj</button>
</form>
</div>
</body>
</html>"""

if __name__ == "__main__":
    app.run()

