import resources.lib.vrvlib as vrvlib
import getpass

email = raw_input("Email: ")
password = getpass.getpass("Password: ")

if email and password:
    session = vrvlib.VRV(email=email,password=password,key="RHUPiy8MFEj6z0tIu46cU2bAQu9DVRQWZ87838TEhsN1JpevcqtzL1J9rF3f",secret="6g5Pp1jfY7HlZE79InmGJqhsYJWYBJAkm4sgJHdwdTnKbxJIiccusrtyokVr")
    cms_url = session.index.links['cms_index.v2'].rstrip('index')

    watchlist = session.get_watchlist(100)
    wl_items = dict()
    for item in watchlist.items:
        wl_items[item.panel.id] = item
        print("Fetched {} \"{}\" from channel \"{}\" with ID {} from watchlist.".format(item.panel.ptype,item.panel.title,item.panel.channel_id,item.panel.id))

    #series = session.get_cms(wl_items[0].panel.resource)
    channels_data = session.get_cms(session.links['channels'])

    movie_listing = session.get_cms(wl_items['G6JQ2DXXR'].panel.links['resource'])
    nid = 'G6JQ2DXXR'
    movies_list = session.get_cms(cms_url + 'movie_listings/' + nid)
    print(movie_listing)
    movies = session.get_cms(movie_listing.movies_path)
    print(movies.items)
    
    ch_data = session.get_cms(channels_data.items[1].links['channel/cms_channel'])
    ch_series = session.get_cms(ch_data.links['channel/series'])
    ch_series_list = list()         
    limit = 20
    index = 0
    while 'continuation' in ch_series.links:                              
        for item in ch_series.items:
            ch_series_list.append(item)
            print(u"Fetched {} \"{}\" from channel \"{}\" with ID {}".format(item.ptype, item.title, item.channel_id, item.id))
        
        index += limit
        next_batch_link = "{}series?channel_id={}&cont={}&limit={}&mode=channel".format(cms_url,ch_data.id,index,limit)
        
        print("Next lookup link is " + next_batch_link)
        ch_series = session.get_cms(next_batch_link)
        
        #if ch_series.links.get('continuation') != None:
        #    ch_series = session.get_cms(ch_data.links.get('continuation'))
        #else:
        #    break
