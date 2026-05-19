
var sLang = "en";
if( region=="eur" ){
	// Chilli europa
	var sUrl = 'https://chillieurope.shaperbuddy.com';
}else if( region=="usa" ){
	// Chilli Usa
	var sUrl = 'https://chilliusa.shaperbuddy.com';
}else if( region=="bali" ){
	// Chilli Bali
	var sUrl = 'https://chillibali.shaperbuddy.com';
}else if( region=="bra" ){
	// Chilli Brazil
	var sUrl = 'https://chillibrasil.shaperbuddy.com';
	
}else if( region=="chl" ){
	// Chilli Chile
	var sUrl = 'https://chillichile.shaperbuddy.com';
	
	
	
}else if( region=="jpn" ){
	// Chilli Japan
	var sUrl = 'https://chillijapan.shaperbuddy.com';
	
}else if( region=="aus" ){
	// Chilli Australia
	
	var sUrl = 'https://chilli.shaperbuddy.com';
}else{
	// Just in case (Chilli Australia)
	var sUrl = 'https://chilli.shaperbuddy.com';
}



var sUrlWebsite = "https://chilli.shaperbuddy.com";
var sUrlShop = sUrlWebsite;

// global objects to store data
var shaperbuddy = {};
shaperbuddy.shop = {};

 function getQueryString(name) {
 	name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
 	var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
 	results = regex.exec(location.search);
 	return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
 }

/*used to populate the mega menu*/
function service_SurfboardModels(){
	// Isto deixa USa buscar em USA e EUR/AUS buscar em AUS
	var endpoint = sUrlWebsite;
	if( region=="usa" || region=="eur" || region=="bra"){
		endpoint = sUrl;
	}

	$.ajax({
		url: endpoint+'/api/v1/surfboardmodels?mode=fast',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		$('.mm_0 ul').empty();
		$('.mm_4 ul').empty();
		$('.mm_6 ul').empty();
		for(var key in data) {
			//if(  region=="aus" ) {
				var min_price = data[key].min_price;
				var currency_iso = data[key].currency.iso;
				var currency_symbol = data[key].currency.symbol;
			//}else{
			//	var min_price = "";
			//	var currency_iso = "";
			//	var currency_symbol = "";
			//}
			var waveSize = data[key].wavesize.min;
			var model = data[key].surfboardmodel;
			var boardImg = data[key].img_420;
			var id = data[key].id_surfboardmodel;
			$('.mm_'+waveSize+' ul').append('<li><a href="/surfboards/detail.php?id='+id+'" data-boardimg="'+boardImg+'" data-min_price="'+min_price+'" data-currencyiso="'+currency_iso+'" data-currencysymbol="'+currency_symbol+'" data-model="'+model+'">'+model+'</a></li>');

			//$('#surfboards-menu-mobile').append('<li><a href="#">'+model+'</a></li>');

			//$('#waves-size-'+waveSize+' li').after().append('<li><a href="/surfboards/detail.php?id='+id+'">'+model+'</a></li>');
			//$('#waves-size').append('<li><a href="/surfboards/detail.php?id='+id+'">'+model+'</a></li>');
			$('#waves-size-'+waveSize).after('<li><a href="/surfboards/detail.php?id='+id+'">'+model+'</a></li>');

			//waves-size-0

			$('.ftws_'+waveSize).append('<li><a href="/surfboards/detail.php?id='+id+'">'+model+'</a></li>');
		}
	});
}



function service_SurfboardModels_widget(){
		init_FeaturedBoards( $('.featuredboards_home') );
		// trick to hide the first separator
		/*
		var winWidth = $(window).width();
		var itemWidth;
		if(winWidth>1200){
			itemWidth = 265;
		} else if(winWidth<1200 && winWidth>992){
			itemWidth = 235;
		} else if(winWidth<992 && winWidth>768){
			itemWidth = 245;
		}
		$('.featuredboards_track').css('left','-'+itemWidth+'px');
		*/

        if( region!="aus" ){
		$.ajax({
			url: sUrl+'/api/v1/surfboardmodelpricenetwork',
			method: 'GET',
			context: document.body
		}).done(function(data) {
			var symbol = data.currency.symbol;
			var iso = data.currency.iso;
			var _prices = data.prices;
			for( key in _prices ){
				if( _prices[key].price != "" ){
					$(".featuredboards_track .changeprice[data-id_surfboardmodel="+_prices[key].id+"] .board_info .board_price").removeClass("no_price").append( symbol + "" + _prices[key].price + " " + iso );	
				}
			}
		})
	}
}

//populate carousel
function service_homeSliderImg(){
	$.ajax({
		url: sUrlWebsite+'/api/v1/cms/zones/42/objects',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var imgContainer = $('.main_destaque .carousel-inner');
		var bulletContainer = $('.main_destaque .carousel-indicators')
		//imgContainer.empty();
		bulletContainer.empty();
		var keyI = 0;
		for(var key in data) {

			//check if link exists
			if( data[key].hpurl != null ) link = data[key].hpurl;
			else link = '#';

			//--------------------------------------------------------
			//build html here

			//manipulate for testing purposes - it works
			//data[key].hpurl = 'http://www.surftotal.com';

			var item = '<div class="item">';

			//open link if it exists
			if( data[key].hpurl != null ){
				item += '<a href="'+data[key].hpurl+'">';
			}

			item += '<img src="'+data[key].bannerimg+'" alt="'+data[key].hpresume+'"> \
			      	 <div class="carousel-caption"></div>				\
			      	 <div class="carousel-caption">					\
			      	 	<p class="hpslidertext_1">'+data[key].hptitle+'</p>					\
			      	 	<p class="hpslidertext_2">'+data[key].hpresume+'</p>';

			//close link, if it exists..
			if( data[key].hpurl != null ){
				item += '</a>';
			}

			item += '</div>\
			</div>';

			imgContainer.append(item);

			bulletContainer.append('<li data-target="#chilli_carousel" data-slide-to="'+keyI+'"></li>');

			keyI++;
		}

		imgContainer.find('.item:first').addClass('active');
		bulletContainer.find('li:first').addClass('active');

		setTimeout(function(){
			$('.main_destaque').removeClass('md_loadingimgs');
		}, 200);

	});
}



function service_homeLinksDestaque(){
	$.ajax({
		url: sUrlWebsite+'/api/v1/cms/zones/43/objects',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		$('.links_destaque .ld_1 a img').attr('src', data[0].hpthumb);
		$('.links_destaque .ld_1 .ld_item_title').text(data[0].hpresume);
		$('.links_destaque .ld_1 a').attr('href', data[0].hpurl);
		$('.links_destaque .ld_1 a .lditem_toplayer p').html(data[0].hptitle);
		$('.links_destaque .ld_2 a img').attr('src', data[1].hpthumb);
		$('.links_destaque .ld_2 .ld_item_title').text(data[1].hpresume);
		$('.links_destaque .ld_2 a').attr('href', data[1].hpurl);
		$('.links_destaque .ld_2 a .lditem_toplayer p').html(data[1].hptitle);
	});
}


//home video
function service_homeVideo(){

	$.ajax({
		url: sUrlWebsite+'/api/v1/cms/zones/44/objects?top=1',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		$('#video-title').text(data[0].hptitle);
		$('#video-date').append(data[0].dt_publication.en);

		var isYoutube = data[0].hpurlvideo.indexOf('youtu') > -1;
		if(isYoutube){
			videoId = youtube_parser(data[0].hpurlvideo);
			videoSource = 'youtube';
		} else {
			var vimeoId = data[0].hpurlvideo.split('/');
			videoId = vimeoId[vimeoId.length - 1];
			videoSource = 'vimeo';
			videoUrl = 'https://player.vimeo.com/video/'+videoId;
		}

		if(videoSource=='vimeo'){
			videoHtml = '<iframe src="https://player.vimeo.com/video/'+videoId+'" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>';
		} else if(videoSource=='youtube'){
			videoHtml = '<iframe src="https://www.youtube.com/embed/'+videoId+'" frameborder="0" allowfullscreen></iframe>';
		}

		$('.video_home_video').append(videoHtml);

	});
}


// 30.08.2017: done on the homepage with curl now
function service_homeNews(id_team){
	var url = sUrlWebsite+'/api/v1/cms/zones/45/objects';
	if(id_team!=undefined){
		url += '?id_team='+id_team;
	}

	$.ajax({
		url: url,
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var length = data.length;
		var container = $('.lfc_articles_container');
		container.empty();
		for(i=0;i<3;i++){
			var multimediaType = data[i].multimedia[0].id_cmsconteudomultimediatype;
			var fileUrl = data[i].multimedia[0].filename;
			var title = data[i].hptitle;
			var pubDate = data[i].dt_publication.en;
			var resume = data[i].hpresume;
			var id_cmsconteudo = data[i].id_cmsconteudo;


			container.append('																	\
				<div class="col-sm-4 lfc_article_wrapper lfca_'+i+'">							\
					<div class="lfc_article">													\
						<a href="/blog/detail.php?id='+id_cmsconteudo+'">			\
							<div class="lfc_image">												\
								<img src="'+fileUrl+'" class="img-responsive">					\
								<div class="lfc_title">											\
									<p class="lfc_titletitle">'+title+'</p>						\
								</div>															\
							</div>																\
						</a>																	\
					</div>																		\
				</div>																			\
			');


			if(multimediaType === '178'){
				var videoUrl = data[i].multimedia[0].url;
				var isYoutube = videoUrl.indexOf('youtu') > -1;
				if(isYoutube){
					var videoId = youtube_parser(videoUrl);
					fileUrl = 'https://img.youtube.com/vi/'+videoId+'/0.jpg';
					$('.lfca_'+i+' .lfc_article .lfc_image img').attr('src', fileUrl);
				} else {
					var vimeoId = videoUrl.split('/');
					vimeoId = vimeoId[vimeoId.length - 1];
					$('.lfca_'+i).addClass('vimeo_'+vimeoId);
					$.ajax({
						url: 'https://vimeo.com/api/v2/video/'+vimeoId+'.xml',
						method: 'GET',
						context: document.body
					}).done(function(data) {
						var data = $(data);
						var id = data.find('id').text();
						var vimeoFileUrl = data.find('thumbnail_large').text();
						$('.vimeo_'+id).find('.lfc_image img').attr('src', vimeoFileUrl);
					});
				}
			}


		}
	});
}

/*
<div class="col-sm-4 lfc_article_wrapper lfca_'+i+'">							\
	<div class="lfc_article">													\
		<a href="#">															\
			<div class="lfc_image">												\
				<img src="'+fileUrl+'" class="img-responsive">					\
			</div>																\
			<div class="lfc_title">												\
				<p class="lfc_titletitle">'+title+'</p>							\
				<p class="lfc_titleinfo">Posted on: '+pubDate+'</p>				\
			</div>																\
			<div class="lfc_text"><p>'+resume+'</p></div>						\
			<span class="btn btn-primary">View post</span>						\
		</a>																	\
	</div>																		\
</div>
*/




function initInstagram(){
	$('.instaimgs_wrapper').empty();
    $.ajax({
    	type: "GET",
        dataType: "jsonp",
        cache: false,
        url: "https://api.instagram.com/v1/users/self/media/recent/?access_token=12945741.801a985.f4415a6768184e3f8799d71ca097e978",
        success: function(data) {
        	var data = data.data;
        	var iwIndex = 1;
        	$('.instaimgs_wrapper').each(function(){
        		var t = $(this);
        		var nrOfImgs = t.attr('data-nrofimgs');

        		for(var i = 0; i < nrOfImgs; i++){
		        	var imgThumb = data[i].images.standard_resolution.url;
		        	var imgUrl = data[i].link;
		        	t.append('														\
		        		<div class="it_item">										\
							<a href="'+imgUrl+'" target="_blank">					\
								<img src="'+imgThumb+'" class="img-responsive">		\
							</a>													\
						</div>														\
		        	');
	        	}
        		iwIndex++;
        	});

    		$('.insta_widget').each(function(){
				var t = $(this);
				startInstaWidget(t);
			});		

        }
    });
}





function service_Sprayslist(){

    //$('.sbl_boardslist .row').empty();

    var sprays_html = '<div class="row" style="margin-top:50px">';

	$.ajax({
		url: sUrlWebsite+'/api/v1/art/paint',
		method: 'GET',
		context: document.body
	}).done(function(data) {

        //count the loops to add new rows
        var loops = 0;

        //lazy" data-original="'+img+'"

        for(var key in data) {

            sprays_html += '<div class="col-sm-4 col-xs-12 text-center spray-paint-col">\
                                <a href="#">\
                                    <img class="img-responsive center-block spray-paint-img lazy" data-original="'+data[key].image+'">\
                                    <img src="/images/boardswidget_shadow_double.jpg" class="img-responsive center-block">\
                                    <div class="board_info">\
                                        <span class="board_name">'+data[key].name+'</span>\
                                    </div>\
                                </a>\
                            </div>';

            loops++;

            //close this row and add new row
            if( loops == 3 ){

                sprays_html += '</div><div class="row" style="margin-top:50px">';

                loops = 0;

            }

		}//end for

        //close row

        sprays_html += '</div>';

        $('#sprays-container').append( sprays_html );

        //lazy load images only when doc is ready
        $('document').ready(function(){
            $("img.lazy").lazyload({
                effect : "fadeIn"
            });
        })
	});

    //open the model and show the spray..
	$(document).on('click', '#sprays-container a', function(e){
        e.preventDefault();
		var t = $(this);
		var imgSrc = t.find('.spray-paint-img').attr('src');
		var title = t.find('.board_info span').text();
		$('.spraypimg_wrapper img').attr('src', imgSrc);
		$('.spraypimg_wrapper_title').text(title);

        $('#spraypreview').modal('show');

	});

    //fade
    $(document).on('mouseover', '.spray-paint-col', function(){

        //var el = $(this);

        $('.spray-paint-col').not(this).stop().animate({'opacity':.5});

        $(this).on('mouseout', function(){
            $('.spray-paint-col').not(this).stop().animate({'opacity':1});
        })
    })

}






var boardModelList;
function filterBoards(){
	$('.sbl_boardslist .sblblboard_item').removeClass('sblblbi_visible');
	var filterItems = $('.sblf_tabs .tab-pane');
	var filter = '';
	var query;
	var checkedItemsObj = {};

	var fiIndex = 0;
	filterItems.each(function(){
		var t = $(this);
		var checkedItems = new Array();
		var tChecked = t.find('.sblf_filtercheck:checked');
		tChecked.each(function(){
			var t = $(this);
			var filterValue = '.'+t.attr('data-filtervalue');
			checkedItems.push(filterValue);
		});
		if(checkedItems.length>0){
			checkedItemsObj[fiIndex] = checkedItems;
		} else {
			checkedItemsObj[fiIndex] = ['none'];
		}
		fiIndex++;
	});

	function allCombinations(sets,f,context){
	  if (!context) context=this;
	  var p=[],max=sets.length-1,lens=[];
	  for (var i=sets.length;i--;) lens[i]=sets[i].length;
	  function dive(d){
	    var a=sets[d], len=lens[d];
	    if (d==max) for (var i=0;i<len;++i) p[d]=a[i], f.apply(context,p);
	    else        for (var i=0;i<len;++i) p[d]=a[i], dive(d+1);
	    p.pop();
	  }
	  dive(0);
	}

	allCombinations([checkedItemsObj[0],checkedItemsObj[1],checkedItemsObj[2]], function(filter1,filter2,filter3){
		var option = filter1+''+filter2+''+filter3;
		option = option.replace(/none/g, "");
		filter += option+', ';
	});

	filter = filter.slice(0,-2);
	query = $(filter);
	var nrOfFilterChecked = $('.sblf_tabs .sblf_filtercheck:checked').size();
	if(nrOfFilterChecked==0){
		query = $('.sbl_boardslist .sblblboard_item');
	}
	query.each(function(){
		var t = $(this);
		var img = t.find('.sblbl_boardimg img');
		var src = img.attr('data-imgsrc');
		img.attr('src', src);
	});
	query.addClass('sblblbi_visible');
}
$(function(){
	$(document).on('change', '.sblf_tabs .sblf_filtercheck', function(){
		filterBoards();
	});
});


var bmp_loaded = 0;
function boardModelPage_isLoaded(loaded){
	console.log('loaded:' + loaded);
	bmp_loaded++;;
	if(bmp_loaded==4){
		$('.sblf_filtercheck:first').trigger('change');
	}
}


function toFeet(n) {
    return Math.floor(n / 12) + "'" + (n % 12) + '"';
}

function toInches(n){

    return Math.ceil( n * .039 );

}

/*

/surfboards
gets the boards? yes - where: /surfboards

*/
function service_SurfboardModelsPage(){

    //throw new Error('died before loading boards');

	// Isto deixa USa buscar em USA e EUR/AUS buscar em AUS
	var endpoint = sUrlWebsite;
	if( region=="usa" || region=="eur"  || region=="bali" || region=="bra"  || region=="jpn"){
		endpoint = sUrl;
	}

	console.log('endpoint:' + endpoint);
	$.ajax({
		url: endpoint+'/api/v1/surfboardmodels',
		method: 'GET',
		context: document.body
	}).done(function(data) {
        var loops = 0;
        var boards_html = '<!--board content goes here-->';
        var tax ='';
        if(region=="jpn"){
        	tax = ' + Tax' ;
        }
       
		boardModelList = data;
		for(var key in data) {

			// FALTA VERIFICAR SE É NEW
			var id_surfboardmodel = data[key].id_surfboardmodel;
			var model = data[key].surfboardmodel;
			var price = data[key].min_price;
			var symbol = data[key].currency.symbol;
			var iso = data[key].currency.iso;
			var img = data[key].img_dynamic;
			//var waveSize = 'ws_'+data[key].wavesize.min;
			var boardType = 'bt_'+data[key].id_surfboardmodeltype;
			var skillLevelObj = data[key].skilllevel;
			var skillLevel = '';
			for(var skill_key in skillLevelObj) {
				skillLevel += 'sl_'+skill_key+' ';
			}


            if(loops == 0) boards_html += '<div class="row">';
            var wave_size_id = parseInt( data[key].wavesize.min * 10 );

            // extra classes are for the filters
            boards_html += '<div class="col-sm-4 col-xs-12 sblblboard_item ws_'+wave_size_id+' '+boardType+' '+skillLevel+'">		\
					<div class="sblbl_board">																	\
						<a href="/surfboards/detail.php?id='+id_surfboardmodel+'&direct=1&region='+ region +'&/'+model.replace(' ','-').toLowerCase()+'">																			\
							<div class="sblbl_board_top">														\
								<div href="#" class="btn btn-warning">New</div>									\
							</div>																				\
							<div class="sblbl_boardimg">														\
								<img src="" class="img-responsive" data-imgsrc="'+img+'?h=450">						\
							</div>																				\
							<div class="board_shadow">															\
								<img src="/images/boardswidget_shadow.png">										\
							</div>																				\
							<div class="board_info">															\
								<span class="board_name">'+model+'</span>										\
								<span class="board_price">'+symbol+''+price+' '+iso+ tax +'</span>						\
							</div>																				\
						</a>																					\
					</div>\
                </div>';

            //PBS: count loops to insert a new row..
            loops++;

            if(loops == 3){
                boards_html += '</div><div class="row">';
                //reset loop counter
                loops = 0;
            }
        }//end for board data

        //close row
        boards_html += '</div>';

        $('.sbl_boardslist').append(boards_html);

        // what happens here..?
		boardModelPage_isLoaded('board_list');
	});
}


/* /surfboards */
function service_SurfboardModelsPage_filter(){
	$('.sblf_tabs .tab-pane').empty();

	// Isto deixa USa buscar em USA e EUR/AUS buscar em AUS
	var endpoint = sUrlWebsite;
	if( region=="usa" || region=="eur"  || region=="bali" || region=="bra" || region=="jpn" ){
		endpoint = sUrl;
	}

	$.ajax({
		url: endpoint+'/api/v1/surfboardmodels',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data) {
			var waveSizeMinMax = data[key].wavesize;
			var wave_size_min_parsed = parseFloat( waveSizeMinMax.min ).toFixed( 0 );
			var wave_size_max_parsed = parseFloat( waveSizeMinMax.max ).toFixed( 0 );		
			// create an uniq valid id / css class			
//			var wave_size_id = parseInt( wave_size_min_parsed * 10 );
			var wave_size_id = parseInt( data[key].wavesize.min  * 10 );
		
			// checks if wave size was already appended
			if( $('.sblffc_wavesize_'+wave_size_id ).size() < 1){
				$('#sblf_wavesize').append('																														\
					<label>																																			\
						<input class="sblf_filtercheck sblffc_wavesize_'+wave_size_id+'" type="checkbox" name="" value="" checked  data-filtervalue="ws_'+wave_size_id+'">	\
						'+wave_size_min_parsed+' - '+wave_size_max_parsed+' '+waveSizeMinMax.measure+' 																\
					</label>																																		\
				');
			}
		}
		boardModelPage_isLoaded('filter_wavesize');
	});


	$.ajax({
		url: sUrl+'/api/v1/surboardmodeltypes',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data) {
			$('#sblf_boardtype').append('																			\
				<label>																								\
					<input class="sblf_filtercheck" type="checkbox" name="" checked value="" data-filtervalue="bt_'+key+'">	\
					'+data[key]+' 																					\
				</label>																							\
			');
		}
		boardModelPage_isLoaded('filter_boardtype');
	});


	$.ajax({
		url: sUrl+'/api/v1/skilllevels',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data) {
			$('#sblf_skilllevel').append('																			\
				<label>																								\
					<input class="sblf_filtercheck" type="checkbox" name="" checked value="" data-filtervalue="sl_'+key+'">	\
					'+data[key]+' 																					\
				</label>																							\
			');
		}
		boardModelPage_isLoaded('filter_skilllevel');
	});
}









var locations = new Array();

function service_Dealers(){

    var container = $('.dealers_list_inner');
	container.empty();

    $.ajax({
		url: sUrl+'/api/v1/dealers',
		method: 'GET',
		context: document.body
	}).done(function(data) {

		var loadedCountrys = new Array();
		var loadedStates = new Array();

		for(var key in data) {
			var t = data[key];
			var country = t.country;
			var countryId = t.id_country
			var state = t.state;
			var stateId = t.id_state;
			var name = t.name;
			var address = t.address;
			var phone = t.phone;
			var email = t.email;
			var lat = t.gpslat;
			var lng = t.gpslong;
            var zip_code = t.zipcode;
            var city = t.city;

            if( lat != '' ){

                var location = [];

                location['name']       = name;
                location['lat']        = lat;
                location['lng']        = lng;
                location['address']    = address;
                location['phone']      = phone;
                location['email']      = email;
                location['url']        = t.url;

                locations.push( location );

            }

			var isCountryLoaded = (loadedCountrys.indexOf(country)>-1);
			var isStateLoaded = (loadedStates.indexOf(state)>-1);
			// BUILD COUNTRY
			if(!isCountryLoaded){
				loadedCountrys.push(country);
				container.append('									\
					<div id="ct_'+countryId+'" class="dl_country country_'+countryId+'">	\
						<p class="dl_countrytitle">					\
							<span>'+country+'</span>				\
						</p>										\
						<div class="container"></div>				\
					</div>											\
				');
				$('.dealers_filter .df_country').append('<option value="'+countryId+'">'+country+'</option>');
			}
			// BUILD STATE
			if(state!= ''){
				if(!isStateLoaded){
					loadedStates.push(state);
					container.find('.country_'+countryId+' .container').append('	\
						<div class="row dl_areatitle">								\
							<div class="col-xs-12">'+state+'</div>					\
						</div>														\
						<div class="row state_'+stateId+'"></div>					\
					');
				}
			}
			//BUILD SHOPS
			var shopTarget;
			if(state!= ''){
				shopTarget = container.find('.country_'+countryId+' .container .state_'+stateId+'');
			} else {
				shopTarget = container.find('.country_'+countryId+' .container');
			}

            // it changes according to country
            var formated_address = '';

            // Australia
            if( countryId == 141 ){
                formated_address = address+'<br>'+city+' '+zip_code;

            }else{
                formated_address = address+'<br>'+zip_code+' '+city;
            }

			shopTarget.append('																							\
				<div class="col-sm-4 dl_item">																			\
					<h5>'+name+'</h5>																					\
					<p class="dli_address">'+formated_address+'</p>\
					<p class="dli_phone">																				\
						<label>Phone:&nbsp;</label>'+phone+'															\
					</p>																								\
					<p class="dli_email">																				\
						<label>Email:&nbsp;</label>'+email+'															\
					</p>\
                    <p class="dli_url">\
                        <label>Site:&nbsp;</label> <a href="'+t.url+'" target="_blank">'+t.url+'</a>\
                    </p>\
					<a href="#" data-lat="'+lat+'" data-lng="'+lng+'" data-title="'+name+'" data-address="'+formated_address+'" class="dli_viewonmaps" data-toggle="modal" data-target="#modal_viewonmaps">View on Google Maps</a>	\
				</div>																									\
			');
			if(phone==''){
				$('.dl_item:last .dli_phone').remove();
			}
			if(email==''){
				$('.dl_item:last .dli_email').remove();
			}
			if(lat==''){
				$('.dl_item:last .dli_viewonmaps').remove();
			}
            if(t.url == '' ){
                $('.dl_item:last .dli_url').remove();
            }
		}

		setListItemHeight($('.dl_item'));
		setMarker(locations);

		$(window).trigger('scroll');
	});
}










function service_TeamList(){
	var container = $('.team_list .row');
	container.empty();
	$.ajax({
		url: sUrlWebsite+'/api/v1/team',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data) {
			var image = data[key].photothumb;
			var country = data[key].country;
			var name = data[key].name;
			var id = data[key].id_team;
			container.append('															\
				<div class="col-sm-4">													\
					<div class="tl_item">												\
						<a href="/team/detail.php?id='+id+'&/'+name.replace(' ','-').toLowerCase()+'">							\
							<div class="tli_img">										\
								<img src="'+image+'" class="img-responsive">			\
							</div>														\
							<div class="tli_name">'+name+'</div>						\
							<div class="tli_location">'+country+'</div>					\
						</a>															\
					</div>																\
				</div>																	\
			');
		}
		setListItemHeight($('.tl_item').parent());
	});
}





function service_TeamDetail_images(){
	var teamMemberId = getQueryString('id');
	var teamMemberSliderImgs = $('.teammember_slider .carousel-inner');
	var teamMemberSliderIndicators = $('.teammember_slider .carousel-indicators');
	teamMemberSliderImgs.empty();
	teamMemberSliderIndicators.empty();
	$.ajax({
		url: sUrlWebsite+'/api/v1/team/'+teamMemberId+'/images',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var loopI = 0;
		for(var key in data) {
			var img = data[key].url;
			teamMemberSliderImgs.append('<div class="item"><img src="'+img+'" alt="..."></div>');
			teamMemberSliderIndicators.append('<li data-target="#chilli_carousel" data-slide-to="'+loopI+'"></li>');
			loopI++;
		}
		teamMemberSliderImgs.find('.item:first').addClass('active');
		teamMemberSliderIndicators.find('.li:first').addClass('active');
	});
}


function service_TeamDetail_video(){
	var teamMemberId = getQueryString('id');
	$.ajax({
		url: sUrlWebsite+'/api/v1/team/'+teamMemberId+'/videos',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data) {
            var description = data[key].description;
            var url = data[key].url;
			var videoId;
			var videoSource;
			var videoUrl = url;
			var isYoutube = videoUrl.indexOf('youtu') > -1;

			if(isYoutube){
				videoId = youtube_parser(videoUrl);
				videoSource = 'youtube';
			} else {
				var vimeoId = videoUrl.split('/');
				videoId = vimeoId[vimeoId.length - 1];
				videoSource = 'vimeo';
				videoUrl = 'https://player.vimeo.com/video/'+videoId;
			}

			$('.videos_carousel .carousel-inner .active .row').append('							\
				<div class="col-sm-4 vc_item_wrapper">											\
					<a href="'+videoUrl+'" class="vc_item" data-videosource="'+videoSource+'" data-id="'+videoId+'">	\
						<div class="vci_img">													\
							<img src="images/dummies/vc_videothumb.jpg" class="img-responsive">	\
							<div class="playbutton">											\
								<img src="/images/vc_playicon.png">								\
							</div>																\
						</div>																	\
						<div class="vci_title">'+description+'</div>								\
					</a>																		\
				</div>																			\
			');

		}

		setVideoPagination($('.videos_carousel'));
		setVideoProperties();
	});
}

//team details
function service_TeamDetail(){

	var teamMemberId = getQueryString('id');

	$.ajax({
		url: sUrlWebsite+'/api/v1/team/'+teamMemberId,
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var id_team = data.id_team;
		var name = data.name;
		var firstName = name.split(' ')[0];
		var country = data.country;
		var description = data.bio;
		var height = data.height;
		var weight = data.weight;
		var stance = data.stance_txt;
		var quiver = data.surfboardmodels;
		var quiverNrOfBoards = quiver.length;
		var socialNetworks = data.socialnetworks;
		var symbol = data.currency.symbol;
		var iso = data.currency.iso;

		$('.tli_name_main, .breadcrumb .active').html(name);
		$('.tli_location').html(country);
		$('.tli_text').html(description);
		$('.tli_firstname, .insta_widget_wrapper h1 span').html(firstName);
		$('.rider-name').html(firstName+"´s");
		$('.tli_height span').html(height);
		$('.tli_weight span').html(weight);
		$('.tli_stance span').html(stance);


		for(var key in socialNetworks){

			var id_socialnetwork = socialNetworks[key].id_socialnetwork;
			var url = socialNetworks[key].url;

			// facebook
			if(id_socialnetwork=='1'){
				$('.tli_follow .getsocial_links ul, .insta_widget_wrapper .getsocial_links ul').append('<li><a href="'+url+'" target="_blank"><img src="/images/social_fb.png"></a></li>');
			}
			//twitter
			if(id_socialnetwork=='2'){
				$('.tli_follow .getsocial_links ul, .insta_widget_wrapper .getsocial_links ul').append('<li><a href="'+url+'" target="_blank"><img src="/images/social_twitter.png"></a></li>');
			}
			//
			if(id_socialnetwork=='3'){
				$('.tli_follow .getsocial_links ul, .insta_widget_wrapper .getsocial_links ul').append('<li><a href="'+url+'" target="_blank"><img src="/images/social_youtube.png"></a></li>');
			}
			// instagram
			if(id_socialnetwork=='4'){
				$('.tli_follow .getsocial_links ul, .insta_widget_wrapper .getsocial_links ul').append('<li><a href="'+url+'" target="_blank"><img src="/images/social_insta.png"></a></li>');

				//prepare the username, like the designer wants it..
				if( url != null ){
					var url_parts = url.split('/');
					$('.getsocial_subtitle').html( '<a href="'+url+'" target="_blank">@'+url_parts[3]+'</a>' );
				}

				initInstagram_team(socialNetworks[key].memberid);
			}
			// vimeo
			if(id_socialnetwork=='5'){
			}

		}


		var nrOfCols = 12/quiverNrOfBoards;
		if(quiverNrOfBoards>=4){
			nrOfCols = 4;
		}
		var quiverI=0;
		for(var key in quiver) {
			if(quiverI<4){
				var img = quiver[key].images[0].image_74;
				var model = quiver[key].surfboardmodel;
				var price = quiver[key].minprice;

				var height = quiver[key].height;
				var wide = quiver[key].wide;
				var thick = quiver[key].thick;

				var modelDesc = '<p><strong>'+model+'</strong> - '+height+' x '+wide+' x '+thick+' L</p>';

				var surfboard_model = quiver[key].id_surfboardmodel;

				$('.tli_ride').append(modelDesc);

				$('.teammember_quiver .container .row').append('												\
					<div class="col-sm-'+nrOfCols+'">															\
						<div class="sblbl_board">																\
							<a href="/surfboards/detail.php?id='+surfboard_model+'">																		\
								<div class="sblbl_boardimg">													\
									<img src="'+img+'" class="img-responsive">									\
								</div>																			\
								<div class="board_shadow">														\
									<img src="/images/boardswidget_shadow.png">									\
								</div>																			\
								<div class="board_info">														\
									<span class="board_name">'+model+'</span>									\
									<span class="board_price">'+symbol+''+price+' '+iso+'</span>				\
								</div>																			\
							</a>																				\
						</div>																					\
					</div>																						\
				');
			}
			quiverI++;
		}

		service_homeNews(id_team);

	});
}







function initInstagram_team(id){
	$('.instaimgs_wrapper').empty();
    $.ajax({
    	type: "GET",
        dataType: "jsonp",
        cache: false,
        url: 'https://api.instagram.com/v1/users/'+id+'/media/recent/?access_token=43180423.0a91f54.5bc57c4d6f1b42289181b61676747075',
        //url: "https://api.instagram.com/v1/tags/pyzelsurfboards/media/recent/?access_token=43180423.0a91f54.5bc57c4d6f1b42289181b61676747075",
        success: function(data) {
        	var data = data.data;
        	var iwIndex = 1;
        	$('.instaimgs_wrapper').each(function(){
        		var t = $(this);
        		var nrOfImgs = t.attr('data-nrofimgs');

        		for(var i = 0; i < nrOfImgs; i++){
		        	var imgThumb = data[i].images.standard_resolution.url;
		        	var imgUrl = data[i].link;
		        	t.append('														\
		        		<div class="it_item">										\
							<a href="'+imgUrl+'" target="_blank">											\
								<img src="'+imgThumb+'" class="img-responsive" alt="'+data[i].caption.text+'">		\
							</a>													\
						</div>														\
		        	');
	        	}
        		iwIndex++;
        	});

    		$('.insta_widget').each(function(){
				var t = $(this);
				startInstaWidget(t);
			});
        }
    });
}









function service_Videos(){
	var teamMemberId = getQueryString('id');
	var videoContainer = $('.videos_carousel .carousel-inner .active .row');

	$.ajax({
		url: sUrlWebsite+'/api/v1/cms/zones/44/objects',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data) {
			var url = data[key].hpurlvideo;
			var posted = data[key].dt_publication.en;
			var videoId;
			var videoSource;
			var videoUrl = url;
			var isYoutube = videoUrl.indexOf('youtu') > -1;

			if(isYoutube){
				videoId = youtube_parser(videoUrl);
				videoSource = 'youtube';
			} else {
				var vimeoId = videoUrl.split('/');
				videoId = vimeoId[vimeoId.length - 1];
				videoSource = 'vimeo';
				videoUrl = 'https://player.vimeo.com/video/'+videoId;
			}

			videoContainer.append('																						\
				<div class="col-sm-4 vc_item_wrapper">																	\
					<a href="'+videoUrl+'" class="vc_item" data-videosource="'+videoSource+'" data-id="'+videoId+'">	\
						<div class="vci_img">																			\
							<img src="" class="img-responsive">															\
							<div class="playbutton">																	\
								<img src="/images/vc_playicon.png">														\
							</div>																						\
						</div>																							\
						<div class="vci_title">'+data[key].hptitle+'</div>																	\
						<div class="vci_addinfo">Posted on: '+posted+'</div>											\
					</a>																								\
				</div>																									\
			');
		}

		setVideoPagination($('.videos_carousel'));
		setVideoProperties();
	});
}




// ---------------------------- PRODUCTS LIST --------------------------//

// shop/surfboards/
//TO-DO: we need to get boards per model.. DONE
// TO-DO: get boards by length, like on JR

function service_productBoardsList(qString){
	if(qString==undefined){
		url = sUrl+'/api/v1/shop/surfboards';
	} else {
		url = sUrl+'/api/v1/shop/surfboards?'+qString;
	}

	// if region is EUR, get only Chilli, as EUR endpoint has other brands
	if( region == 'eur' ){
		url = url+'&id_brand=6883';		
	}

	var boardListContainer = $('.shopitems_list');
	$.ajax({
		url: url,
		method: 'GET',
		context: document.body
	}).done(function(data) {

		boardListContainer.empty();

		var total_surfboards = 0;

		//for loop
		for(var key in data) {

			total_surfboards++;

			var id = data[key].id_surfboard;
			//var img = data[key].img.deck;
			var img = data[key].img_dynamic.deck;
			
			var model = data[key].surfboardmodel;
			var length_inches = data[key].length_inches;
			var width_inches = data[key].width_inches;
			var thickness = data[key].thickness;
			var thickness_inches = data[key].thickness_inches;
			var volume = data[key].volume;
			var old_price = data[key].old_price;
			var new_price_class = "shponlcpi_prodprice";
			var old_price_element = "";
			if( old_price!='' ){
				new_price_class += " newprodprice";
				old_price_element += "<p class='shponlcpi_prodprice oldprodprice'>"+data[key].currency.symbol+" "+old_price+" "+data[key].currency.iso+"</p>";
			}
			if(volume!=''){
				volume = ' = '+volume+' L ';
			}
			/* ========================================================================
		          * Define se a prancha é usada, nova, team e etc...
		          * ======================================================================== */
		          var boardstate = data[key].stocktype;

			var finsystem = data[key].finsystem;
			var fin_no = data[key].fin_no;
			var price = data[key].price;

			if(img == ''){
				img = 'http://images.shaperbuddy.com.s3-website-us-east-1.amazonaws.com/-1/img/boardlist_avatar.png';
			}

			boardListContainer.append('																																					\
				<div class="col-sm-4 col-xs-12 shopboards">																																		\
					<div class="shopitem">																																				\
						<a href="/shop/surfboards/detail.php?id='+id+'&direct=1&region=' + region + '">																													\
							<div class="si_img">																																		\
								<img class="img-responsive lazy" data-original="'+img+'?w=240&sharp=10">																												\
							</div>																																						\
							<div class="shponlc_prodinfo">																																\
								<div class="shponlc_prodinfo_inner">																													\
									<p class="shponlcpi_prodname">'+model+'</p>																											\
									<p class="shponlcpi_proddetails">'+length_inches+' x '+width_inches+' x '+thickness_inches+' '+volume+'<br>'+finsystem+' Fins x '+fin_no+'</p>		\
									<p class="shponlcpi_proddetails proddetail_state">'+boardstate+'</p>\
									<p class="'+new_price_class+'">'+data[key].currency.symbol+' '+price+' '+data[key].currency.iso+'</p>																		\
									'+old_price_element+'\
								</div>																																					\
							</div>																																						\
						</a>																																							\
					</div>																																								\
				</div>																																									\
			');

		}//end for?

		$('.slfh_results').text( total_surfboards );



		$('document').ready(function(){
			$("img.lazy").lazyload({
				effect : "fadeIn"
			});
		})



		//show no results
		if(data.length==0){
			$('.shopitems_list_noresult').show();
			$('.shopitem_alternative').hide();
		} else {
			$('.shopitems_list_noresult').hide();
			$('.shopitem_alternative').show();
		}

	});

}





//function service_productAccessoriesList(qString){
// refactoring this
function products_list(section, qString){
	/*
   	//if( section == 'apparel' && localStorage.getItem("region") == 'eur' )
	if( section == 'apparel' && localStorage.getItem("region") == 'eur' ){
		url = sUrl+'/api/v1/shop/apparel?id_producttag=361';

		if( qString )
   			url += '&'+qString;

	}else if( qString ){
   		
   		url = sUrl+'/api/v1/shop/'+section+'?'+qString;

	}

   	//if( qString )
   		//url = sUrl+'/api/v1/shop/'+section+'?'+qString;
	*/
   	
	if(qString==undefined){
		url = sUrl+'/api/v1/shop/'+section;
	} else {

		// if region is EUR, get only Chilli, as EUR endpoint has other brands
		if( section == 'apparel' && localStorage.getItem("region") == 'eur' ){
			url = sUrl+'/api/v1/shop/apparel?id_producttag=361&'+qString;
		}else{
			url = sUrl+'/api/v1/shop/'+section+'?'+qString;
		}

	}

	//var boardListContainer = $('.shopitems_list');

    var products_placeholder =  $('#products-placeholder');

    var total_products = 0;

    var html = '';

    products_placeholder.empty();

    var loops = 0;

	$.ajax({
		url: url,
		method: 'GET',
		context: document.body
	}).done(function(data) {
        // start new row
        html = '<div class="row">';

		for(var key in data){
            loops++;
            total_products++;

			var brand = data[key].brand;
			var id_product = data[key].id_product;
			var id_brand = data[key].id_brand;
			var name = data[key].name;
			var currency = data[key].currency;
			var minprice = data[key].minprice;
			var colors = data[key].variant_colors;
			var nrOfColors = colors.length;
			var tabContent = '';
			var tabNavContent = '';
			if(nrOfColors==0){
				var name = data[key].name;
				var minprice = data[key].minprice;
				var mainimg = data[key].mainimg;
				tabContent += '<div class="tab-pane fade active in" id="prdvariant_'+key+'_1"><img src="'+mainimg+'?w=400&sharp=10" class="img-responsive"></div>';
				tabNavContent = '';
			} else {
				for(var key2 in colors){
					// this is not supposed to be part of the name..
                    //var name = colors[key2].name;
					var hexcolor = colors[key2].hexcolor;
					var img = colors[key2].img;
					if(key2==0){
						var firstActive = 'active in';
						var firstLinkActive = 'active';
					} else {
						var firstActive = '';
						var firstLinkActive = '';
					}
					tabContent += '<div class="tab-pane fade '+firstActive+'" id="prdvariant_'+key+'_'+key2+'"><img src="'+img+'?w=400&sharp=10" class="img-responsive"></div>';
					tabNavContent += '<li class="'+firstLinkActive+'"><div class="variant_color" href="#prdvariant_'+key+'_'+key2+'" data-toggle="tab" style="background-color:'+hexcolor+';" data-colorname="'+colors[key2].name+'">'+key2+'</div></li>';
				}
			}
            name = name.replace(brand, '');

            html +=
            '<div class="col-sm-4 col-xs-12">\
                <div class="shopitem" data-id_product="'+id_product+'" data-id_brand="'+id_brand+'">\
                    <a href="/shop/accessories/detail.php?id='+id_product+'&shop='+section+'&direct=1&region=' + region + '" data-url="/shop/'+section+'/detail.php?id='+id_product+'&shop='+section+'&direct=1&region=' + region + '">\
                        <div class="tab-content">'+tabContent+'</div>\
                            <div class="shponlc_prodinfo_inner">\
                                <p class="shponlcpi_prodname">'+brand+' '+name+'</p>\
                                <p class="shponlcpi_proddetails"></p>\
                                <p class="shponlcpi_prodprice"><span>'+currency.symbol+'</span>'+minprice+'<span class="currency"> '+currency.iso+'</span></p>\
                            </div>\
                            <div class="variants_nav">\
                                <ul>'+tabNavContent+'</ul>\
                            </div>\
                    </a>\
                </div>\
            </div>';

            // close previous row and open new
            if( loops == 3 ){
                html += '</div><div class="row">';
                loops = 0;
            }
		} // end for

        // close open row
        html += '</div>';
        products_placeholder.append( html );

        // total results on side bar
        $('.slfh_results').text(total_products);

        // and this does what?
        // removes the placeholder div when no text exists..
		$('.shponlcpi_proddetails').each(function(){
			var t = $(this);
			var text = t.text();
			if(text==''){
				t.remove();
			}
		});
	});

}

// PBS: hide / show filters according to device width..
$(document).ready( function(){
    $(window).on("load resize",function(e){
        if($(document).width() < 767 ) {
            $($('.slfg_toggle').attr('href')).collapse('hide');
        }else{
            $($('.slfg_toggle').attr('href')).collapse('show');
        }
    });
});



// this could be the same function as accessories just change the end point..
// done.
function service_productApparelList(qString){
	if(qString==undefined){
		url = sUrl+'/api/v1/shop/apparel';
	} else {
		url = sUrl+'/api/v1/shop/apparel?'+qString;
	}

	var boardListContainer = $('.shopitems_list');
	$.ajax({
		url: url,
		method: 'GET',
		context: document.body
	}).done(function(data) {
		boardListContainer.empty();
		

		for(var key in data){
			var id_product = data[key].id_product;
			var id_brand = data[key].id_brand;

			var mainName = data[key].name;
			var currency = data[key].currency;
			var minprice = data[key].minprice;


			var colors = data[key].variant_colors;
			var nrOfColors = colors.length;
			var tabContent = '';
			var tabNavContent = '';

			if(nrOfColors==0){
				var name = data[key].name;
				var minprice = data[key].minprice;
				var mainimg = data[key].mainimg;
				tabContent += '<div class="tab-pane fade active in" id="prdvariant_'+key+'_1"><img src="'+mainimg+'" class="img-responsive"></div>';
				tabNavContent = '';
			} else {
				for(var key2 in colors){
					var name = colors[key2].name;
					var hexcolor = colors[key2].hexcolor;
					var img = colors[key2].img;


					if(key2==0){
						var firstActive = 'active in';
						var firstLinkActive = 'active';
					} else {
						var firstActive = '';
						var firstLinkActive = '';
					}
					tabContent += '<div class="tab-pane fade '+firstActive+'" id="prdvariant_'+key+'_'+key2+'"><img src="'+img+'" class="img-responsive"></div>';
					tabNavContent += '<li class="'+firstLinkActive+'"><div class="variant_color" href="#prdvariant_'+key+'_'+key2+'" data-toggle="tab" style="background-color:'+hexcolor+';" data-colorname="'+name+'">'+key2+'</div></li>';
				}
			}



			boardListContainer.append('																																					\
				<div class="col-sm-4 col-xs-12">																																		\
					<div class="shopitem" data-id_product="'+id_product+'" data-id_brand="'+id_brand+'">																				\
						<a href="/shop/accessories/detail.php?id='+id_product+'&shop=apparel" data-url="/shop/accessories/detail.php?id='+id_product+'&shop=apparel">						\
							<div class="si_img">																																		\
								<div class="tab-content">'+tabContent+'</div>																											\
							</div>																																						\
							<div class="shponlc_prodinfo">																																\
								<div class="shponlc_prodinfo_inner">																													\
									<p class="shponlcpi_prodname">'+mainName+'</p>																										\
									<p class="shponlcpi_proddetails"></p>																												\
									<p class="shponlcpi_prodprice"><span>'+currency.symbol+'</span>'+minprice+'<span class="currency"> '+currency.iso+'</span></p>						\
								</div>																																					\
								<div class="variants_nav">																																\
									<ul>'+tabNavContent+'</ul>																															\
								</div>																																					\
							</div>																																						\
						</a>																																							\
					</div>																																								\
				</div>																																									\
			');
		}


		$('.shponlcpi_proddetails').each(function(){
			var t = $(this);
			var text = t.text();
			if(text==''){
				t.remove();
			}
		});


		setListItemHeight($('.shopitem').parent());
	});
}

// -------------------------- end PRODUCTS LIST ------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//

// /shop/surfboards and others..
// mainly it builds the filters, then call products of X category..
function service_productBoardsListFilter(shop){
	var url;
	if(shop=='boards'){
		url = sUrl+'/api/v1/shop/surfboards/filters';
	} else if(shop=='apparel'){

		url = sUrl+'/api/v1/shop/apparel/filters';

	} else if(shop=='accessories'){
		url = sUrl+'/api/v1/shop/accessories/filters';
	}else if(shop=='wetsuits'){
		url = sUrl+'/api/v1/shop/wetsuits/filters';
	}else if(shop=='softboards'){
		url = sUrl+'/api/v1/shop/softboards/filters';
	}else if(shop=='accessories'){
		url = sUrl+'/api/v1/shop/softboards/filters';
	}

	$.ajax({
		url: url,
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var filterListContainer = $('.slf_filterlist');
		var rangeValueItems = new Array('6', '7', '11');
		var flcIndex = 1;
		
		

		for(var key in data){
			var id = data[key].id;
			var filterName = data[key].name;
			var filterVar = data[key].var;
			var filterItems = data[key].item;
			var itemsufix = data[key].itemsufix;
			if(itemsufix==undefined){
				itemsufix = '';
			}

			filterListContainer.append('																							\
				<div class="slf_group">																								\
					<a class="slfg_toggle" role="button" data-toggle="collapse" href="#collapse'+flcIndex+'" aria-expanded="true">	\
						<div class="slfg_toggle_inner">'+filterName+'</div>															\
					</a>																											\
					<div class="slfg_items collapse in" id="collapse'+flcIndex+'">													\
						<div class="slfg_items_inner" data-filterdataname=""></div>													\
					</div>																											\
				</div>																												\
			');

			var isRangeItem = rangeValueItems.indexOf(id);

			if(isRangeItem>-1){
				var rangeMin = filterItems.min;
				var rangeMax = filterItems.max;
				filterVar = filterVar.split(',');
				$('.slf_group:last').find('.slfg_items_inner').append('														\
					<label>																									\
						<div class="row filterrange_preview">																\
							<div class="col-xs-4 frp_col1">																	\
								<input class="filterdata fr_min" type="text" name="'+filterVar[0]+'" value="" readonly>		\
								<input class="fr_display fr_min_display" id="fr-min-display-'+id+'" value="" readonly>		\
							</div>																							\
							<div class="col-xs-4 frp_col2">TO</div>															\
							<div class="col-xs-4 frp_col3">																	\
								<input class="filterdata fr_max" type="text" name="'+filterVar[1]+'" value="" readonly>		\
								<input class="fr_display fr_max_display" id="fr-max-display-'+id+'" value="" readonly>		\
							</div>																							\
						</div>																								\
						<div class="filterrange_'+id+' filterrange" data-min="'+rangeMin+'" data-max="'+rangeMax+'"></div>	\
					</label>																								\
				');

				$('.slf_group:last').find('.slfg_items_inner').attr('data-filtertype', 'range');
				$('.slf_group:last').find('.slfg_items_inner').attr('data-filterdataname', filterVar);
				$('.slf_group:last').find('.slfg_items_inner').attr('data-filterdataname_min', filterVar[0]);
				$('.slf_group:last').find('.slfg_items_inner').attr('data-filterdataname_max', filterVar[1]);
				startBoardSizeSlider('filterrange_'+id+'', rangeMin, rangeMax);

			} else {

				//for(var key in filterItems){
				
				
				
                $.each( filterItems, function( key, value ){
					//key = key.trim();
					
                	
					
                    $('.slf_group:last').find('.slfg_items_inner').append('														\
						<label data-itemsufix="'+itemsufix+'">																	\
							<input class="sblf_filtercheck filterdata" type="checkbox" name="'+filterVar+'" value="'+key.trim()+'">	\
							'+filterItems[key]+' 																				\
						</label>																								\
					');

                })

				//}

				$('.slf_group:last').find('.slfg_items_inner').attr('data-filtertype', 'list');
				$('.slf_group:last').find('.slfg_items_inner').attr('data-filterdataname', filterVar);

			}

			flcIndex++;
		}

		$('.slfg_items_inner input[name=id_finsystem_nr]').parent().append(' Fins');


		if(isMobile){
			$('.slf_filterlist .slfg_toggle').trigger('click');
		}

	//try to mark the model of the board as selected if in url query string
	var board_model = getQueryString('model');

	if( board_model != '' ){

		// accept multiple models id	
		$.each( board_model.split(','), function(k, v){

			$('.filterdata[value="'+v+'"]').attr('checked',true)

		})
		
	}

        //PBS: try to mark the technology of the board aas selected if in url query string
        var technology = getQueryString('technology');

        if( technology != '' ){
            $('.filterdata[name="id_surfboardconstructiontype"][value="'+technology+'"]').attr('checked',true)
        }


		//PBS: try to mark the technology of the board aas selected if in url query string
		var id_producttag = getQueryString('id_producttag');

		if( id_producttag != '' ){
			$('.filterdata[name="id_producttag"][value="'+id_producttag+'"]').attr('checked',true)
		}

        // usedstate
        var id_usedstate = getQueryString('id_usedstate');
        var id_usedstate_split = id_usedstate.split(",");
       
        if( id_usedstate != "" ){
	        $('.filterdata[name="id_usedstate"').prop('checked', false);

	        for (key in id_usedstate_split){
	        	      if( id_usedstate_split[key] != '' ){
		          $('.filterdata[name="id_usedstate"][value="'+id_usedstate_split[key]+'"]').prop('checked', true);
		      }	
	        }
	}else{
		// 02.08.2016: set as default new surfboards..
        		$('[name="id_usedstate"]:input[value="0"]').prop( 'checked', true );
	}
        

        // set length
        var length = getQueryString('length');

        if( length != '' ){

            var length_inches = toInches( length );
            //var length_feet = toFeet( length );

            startBoardSizeSlider( "filterrange_6", window.rangeMin, window.rangeMax, length_inches, length_inches );
            //startBoardSizeSlider( "filterrange_6", 50, 50 );

        }

        

		//this sets the filter, does stuff, and then call all the boards..
		//defined at shop_boards.js
		getStandarDimensionsFilter();

	});
}


// --------------------------  PRODUCTS DETAIL -------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//
// ---------------------------- ------------- --------------------------//

function setProductImgs(imgArray){
	// --- IMG VIEWR
	var imgs = imgArray;
	$('.sld_imgviewr .tab-content').empty();
	$('.sld_imgviewr .sld_imgviewr_thumbswrapper').empty();
	var imgLoopI = 1;
	for(var key in imgs){
		//var imgUrl = imgs[key].url;
		var imgUrl = imgs[key].img_dynamic;
		$('.sld_imgviewr .tab-content').append('					\
				<img src="'+imgUrl+'?w=600&sharp=10" class="img-responsive" style="margin-bottom: 5px">		\
		');
		
		imgLoopI++;
	}
	$('.sld_imgviewr .tab-content .tab-pane:first').addClass('active');
	$('.sld_imgviewr .tab-content .tab-pane:first').addClass('in');
	
	if(1==2){
		var allThumbs = $('.sld_imgviewr_thumbswrapper img');
		var nrOfItems = allThumbs.size();
		var loadedImgs = 0;
		allThumbs.one("load", function() {
			loadedImgs++;
			if(loadedImgs===nrOfItems){
				verticalCenterThumbs();
			}
		}).each(function() {
			if(this.complete) $(this).load();
		});
	
	
		$(window).resize(function(){
			verticalCenterThumbs();
		});
	}
	function verticalCenterThumbs(){
		var imgViewrHeight = $('.sld_imgviewr').height();
		var imgViewrthumbswrapper = $('.sld_imgviewr_thumbswrapper').height();
		var thumbsCenter = (imgViewrHeight/2)-(imgViewrthumbswrapper/2);
		$('.sld_imgviewr_thumbswrapper').stop().animate({ 'margin-top': thumbsCenter });
	}
	// --- end IMG VIEWR

	if(nrOfItems==1){
		$('.sld_imgviewr_thumbswrapper').parent().hide();
	}
}


function verticallyCenterThumbs(){

	var allThumbs = $('.sld_imgviewr_thumbswrapper img');
	var nrOfItems = allThumbs.size();
	var loadedImgs = 0;
	allThumbs.one("load", function() {
		loadedImgs++;
		if(loadedImgs===nrOfItems){
			verticalCenterThumbs();
		}
	}).each(function() {
		if(this.complete) $(this).load();
	});


	$(window).resize(function(){
		verticalCenterThumbs();
	});
	function verticalCenterThumbs(){
		var imgViewrHeight = $('.sld_imgviewr').height();
		var imgViewrthumbswrapper = $('.sld_imgviewr_thumbswrapper').height();
		var thumbsCenter = (imgViewrHeight/2)-(imgViewrthumbswrapper/2);
		$('.sld_imgviewr_thumbswrapper').stop().animate({ 'margin-top': thumbsCenter });
	}
	// --- end IMG VIEWR
	
	
}

function setOtherProducts(otherproducts) {
	if (otherproducts == '' || otherproducts == undefined ){
		$('.youmaybeinterested').empty();
	}

	$('.ymbi_prodlist > .container > .row').empty();
	for(var key in otherproducts){
		var id = otherproducts[key].id;
		var id_producttypeOther = otherproducts[key].id_producttype;
		var id_variant = otherproducts[key].id_variant;
		var id_type = otherproducts[key].id_type;
		var name = otherproducts[key].name;
		var price = otherproducts[key].price;
		var img = otherproducts[key].img;
		var product_type = otherproducts[key].producttype.toLowerCase();

		//trick..
		if( product_type == 'surfboard' ) product_type = 'surfboards';

		//must get category of this product..
		$('.ymbi_prodlist > .container > .row').append('															\
			<div class="col-sm-2 col-xs-6">																			\
				<div class="shopitem">																				\
					<a href="/shop/'+product_type+'/detail.php?id='+id+'&shop='+product_type+'">																						\
						<div class="si_img">																		\
							<img src="'+img+'" class="img-responsive">												\
						</div>																						\
						<div class="shponlc_prodinfo">																\
							<div class="shponlc_prodinfo_inner">													\
								<p class="shponlcpi_prodname">'+name+'</p>											\
								<p class="shponlcpi_prodprice">'+price+'</p>		\
							</div>																					\
							<div href="#" data-prdid="'+id+'" class="btn-addtocart addtocart addtocart_singleqty" data-id_product="'+id+'" data-id_producttype="'+id_producttypeOther+'" data-variant="">Add To Cart</div>		\
						</div>																						\
					</a>																							\
				</div>																								\
			</div>																									\
		');
	}
}







function service_productBoardsList_detail(){

	//alert('here');

	var boardId = getQueryString('id');
	$.ajax({
		url: sUrl+'/api/v1/shop/surfboards/'+boardId,
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var id_surfboard = data[0].id_surfboard;
		var id_producttype = data[0].id_producttype;
		var imgs = data[0].img;
		var boardName = data[0].surfboardmodel;
		var boardPrice = data[0].price;
		var currency_iso = data[0].currency.iso;
		var currency_symbol = data[0].currency.symbol;
		var promo = data[0].promo;
		var boardSize = data[0].length_inches;
		var boardWidth = data[0].width_inches;
		var boardThickness = data[0].thickness_inches;
		var boardVolume = data[0].volume;
		var tailShape = data[0].tailname;
		var finSystem = data[0].finsystem +' '+ data[0].finsystemoption +' '+ data[0].fin_no +'fin setup';
		var construction = data[0].surfboardconstructiontype;
		var glassing = data[0].glassing;
		var condition = data[0].condition;
		var waveSize = data[0].wh_min +' - '+ data[0].wh_max +' '+ data[0].wh_measure;
		// ---
		var skillLevel = data[0].skilllevel;
		var skillLevelString = '';
		for(var key in skillLevel){
			skillLevelString += skillLevel[key]+', ';
		}
		skillLevelString = skillLevelString.slice(0, -2);
		// ---
		var waveType = data[0].wavetype_txt;
		var locationName = data[0].location.name;
		var locationAddress = data[0].location.address;
		var locationCountry = data[0].location.country;
		var locationLat = data[0].location.gpslat;
		var locationLng = data[0].location.gpslong;
		var description = data[0].description;
		var paymentSecurity = data[0].payment_security_txt;
		var shippingText = data[0].shipping_txt;
		var otherproducts = data[0].otherproducts;
		var old_price = data[0].old_price;
		/* ========================================================================
	      * Define se a prancha é usada, nova, team e etc...
	      * ======================================================================== */
	      var boardstate = data[0].stocktype;


		if(id_producttype=='1' || id_producttype=='4'){
			$('.sldi_addtocart .addproduct_qty').prop('readonly', true).val(1);
		}

		$('.pp_currencysymbol').html(currency_symbol);
		$('.pp_currencyiso').html(currency_iso);

		//this does what?...
		setProductImgs(imgs);


		$('.breadcrumb .active').html(boardName+' '+boardSize);

		$('.prod_top').html('ID '+id_surfboard);
		$('.prod_title').html(boardName);
		$('.prod_title_size').html(boardSize);
		$('.prod_price .pprice_value').html(boardPrice);
		$('.prod_state_title').html(boardstate);
		if( old_price!='' ){
			$('.pprice_value').closest('.prod_price').addClass('newprice');
			$('.oldprice').html(old_price);
			$('.old_prod_price').fadeIn("slow");
		}

        $('.promo_wrapper').empty();

		for(var key in promo){
			var id = key;
			var text = promo[key];
			if(id!='-1'){
				$('.promo_wrapper').append('<p class="promo_disclaimer" style="background-image: url(/images/icon_'+id+'.jpg);">'+text+'</p>');
			} else {
				$('.promo_wrapper').append('<p class="promo_disclaimer" style="background-image: url(/images/icon_45667.jpg);">'+text+'</p>');
			}
		}
		$('.bd_size').html(boardSize);
		$('.bd_width').html(boardWidth);
		$('.bd_thickness').html(boardThickness);
		$('.bd_volume').html(boardVolume);
		$('.bf_tailshape span').html(tailShape);
		$('.bf_finsystem span').html(finSystem);
		$('.bf_construction span').html(construction);
		$('.bf_glassing span').html(glassing);
		$('.bf_condition span').html(condition);
		$('.bf_wavesize span').html(waveSize);
		$('.bf_skilllevel span').html(skillLevelString);
		$('.bf_wavetype span').html(waveType);
		$('.sld_stocklocation strong').html(locationName);
		$('.sld_stocklocation .sldsl_text').html(locationAddress);
		$('.sld_stocklocation .sldsl_text').append('<br>'+locationCountry+'<br><br>');
		$('.sld_stocklocation a').attr('href', 'https://www.google.com/maps/dir/Current+Location/'+locationLat+','+locationLng); //https://www.google.com/maps/dir/Current+Location/'+locationLat+','+locationLng
		$('.sld_description .sldd_text').html(description);
		$('.sld_paymentandsecurity .sldps_text').html(paymentSecurity);
		$('.sld_shipping .sldshipping_text').html(shippingText);

		setOtherProducts(otherproducts);

        //$('.sldi_addtocart .addtocart').attr('data-id_product', id_surfboard);
        //$('.sldi_addtocart .addtocart').attr('data-id_producttype', id_producttype);

        // PBS: work here
        $('#btn-add-to-cart').attr('data-id_product', id_surfboard);
        $('#btn-add-to-cart').attr('data-id_producttype', id_producttype);

        var is_on_cart = $.grep( surfboards_id_on_cart, function( value ){

            return value == boardId;

        })

        if( is_on_cart.length > 0 ){

            var el = $("#btn-add-to-cart[data-id_product='" + is_on_cart + "']");

            el.html('<i class="glyphicon glyphicon-ok"></i> ADDED TO CART');
            el.addClass('disabled');

        }else if( $("#btn-add-to-cart").hasClass('disabled') ){

            var el = $("#btn-add-to-cart");

            el.removeClass('disabled');
            el.html('<i class="glyphicon glyphicon-shopping-cart"></i> ADD TO CART');

        }

        if(construction==''){
			$('.bf_construction').hide();
		}
		if(glassing==''){
			$('.bf_glassing').hide();
		}
		if(condition==''){
			$('.bf_condition').hide();
		}
	});
}














function service_productAccessories_detail(){
	var variantsData;
	var id_product;
	var id_producttype;

	$(document).on('click', '.vc_innactive', function(e){
		e.preventDefault();
	});

	$(document).on('click', '.variant_container ul li a:not(.vc_innactive)', function(e){
		e.preventDefault();
		var t = $(this);
		var vContainer = t.closest('.variant_container');
		var id_variant = '';
		var old_price = '';
		var price = '';
		var matchFound_hascomb = false;
		var matchFound_findcomb = false;

		vContainer.find('.v_selected').removeClass('v_selected');
		t.addClass('v_selected');

		var activeV1 = $('.vc_1 ul li a.v_selected').parent().attr('data-id');
		var activeV2 = $('.vc_2 ul li a.v_selected').parent().attr('data-id');
		var activeV3 = $('.vc_3 ul li a.v_selected').parent().attr('data-id');
		if(activeV1 == undefined){
			activeV1 = '';
		}
		if(activeV2 == undefined){
			activeV2 = '';
		}
		if(activeV3 == undefined){
			activeV3 = '';
		}

		for(var key in variantsData){
			var variant1 = variantsData[key].variant1;
			var variant2 = variantsData[key].variant2;
			var variant3 = variantsData[key].variant3;

			if(activeV1==variant1 && activeV2==variant2 && activeV3==variant3){
				id_variant = variantsData[key].id_variant;
				matchFound_hascomb = true;

				old_price = variantsData[key].old_price;
				price = variantsData[key].price;
				break;
			}
		}

		if(matchFound_hascomb){
			for(var key in variantsData){
				var curr_id_variant = variantsData[key].id_variant;
				if(curr_id_variant == id_variant){
					var variantImgs = variantsData[key].img;
					matchFound_findcomb = true;
					break;
				}
			}
			setProductImgs(variantImgs);
			
			if(region=="jpn"){
				$('.pprice_value').html(price);
			}else {
				$('.pprice_value').html(price);
			}
			$('.pp_oldprice').html(old_price);
			if(old_price==''){
				$('.oldprice_wrapper').hide();
			} else {
				$('.oldprice_wrapper').show();
			}

            /*
			$('.sldi_addtocart .addtocart').attr('data-id_product', id_product);
			$('.sldi_addtocart .addtocart').attr('data-id_producttype', id_producttype);
			$('.sldi_addtocart .addtocart').attr('data-variant', id_variant);
			*/

            $('#btn-add-to-cart').attr('data-id_product', id_product);
            $('#btn-add-to-cart').attr('data-id_producttype', id_producttype);
            $('#btn-add-to-cart').attr('data-variant', id_variant);

		}

		// ---------- FILTER AVAILABLE COMBINATIONS ------------- //
		var variantNr = t.closest('.variant_container').attr('data-variant');
		if(variantNr=='1'){
			var variantAvailableArray = new Array();
			for(var key in variantsData){
				var lVariant1 = variantsData[key].variant1;
				if(lVariant1==activeV1){
					if(variantAvailableArray.indexOf(variantsData[key].variant2)<0){
						variantAvailableArray.push(variantsData[key].variant2);
					}
					if(variantAvailableArray.indexOf(variantsData[key].variant3)<0){
						variantAvailableArray.push(variantsData[key].variant3);
					}
				} else {
					continue;
				}
			}

			$('.vc_2 ul li a').addClass('vc_innactive');
			$('.vc_3 ul li a').addClass('vc_innactive');;
			$('.vc_2 ul li a, .vc_3 ul li a').each(function(){
				var t = $(this);
				var tVariantName = t.parent().attr('data-id');
				var tVariantAvailable = variantAvailableArray.indexOf(tVariantName);
				if(tVariantAvailable>-1){
					t.removeClass('vc_innactive');
				}
			});

			var vc2_isSelectedInnactive = $('.vc_2 ul li a.v_selected.vc_innactive').size();
			var vc3_isSelectedInnactive = $('.vc_3 ul li a.v_selected.vc_innactive').size();

			if(vc2_isSelectedInnactive>0){
				$('.vc_2 ul li a:not(.vc_innactive)').first().trigger('click');
			}
			if(vc3_isSelectedInnactive>0){
				$('.vc_3 ul li a:not(.vc_innactive)').first().trigger('click');
			}
		}
		// -------- end FILTER AVAILABLE COMBINATIONS ----------- //

	});

	var boardId = getQueryString('id');
	var shop = getQueryString('shop');

	$('.bc_shop').text(shop);
	if(shop=='apparel'){
		$('.bc_shop').attr('href', '/shop/apparel?direct=1&region=' + region);
	
	} else if(shop=='wetsuits'){
		$('.bc_shop').attr('href', '/shop/wetsuits?direct=1&region=' + region);
	
	} else if(shop=='softboards'){
		$('.bc_shop').attr('href', '/shop/softboards?direct=1&region=' + region);
		
	
	} else {
		$('.bc_shop').attr('href', '/shop/accessories?direct=1&region=' + region);
	}

	$.ajax({
		url: sUrl+'/api/v1/shop/'+shop+'/'+boardId,
		method: 'GET',
		context: document.body
	}).done(function(data) {
        var brand = data[0].brand;

		var name = data[0].name.replace(brand, '');
		var currency_symbol = data[0].currency.symbol;
		var currency_iso = data[0].currency.iso;
		var description = data[0].description;
		var spec = data[0].spec;
		var paymentSecurity = data[0].payment_security_txt;
		var shippingText = data[0].shipping_txt;
		var promo = data[0].promo;
		var otherproducts = data[0].otherproducts;
		var videos = data[0].videos;

		var variantColorsSize = data[0].variant_colors.length;

		if(variantColorsSize==0){
			var old_price = data[0].old_price;
			var price = data[0].minprice;
			$('.pprice_value').html(price);
			$('.pp_oldprice').html(old_price);
			if(old_price==''){
				$('.oldprice_wrapper').hide();
			} else {
				$('.oldprice_wrapper').show();
			}
		}

		var variantImgs = data[0].variants[0].img;
		setProductImgs(variantImgs);

		var id_product = data[0].id_product;
		var id_producttype = data[0].id_producttype;
		var id_variant = data[0].variants[0].id_variant;

        /*
		$('.sldi_addtocart .addtocart').attr('data-id_product', id_product);
		$('.sldi_addtocart .addtocart').attr('data-id_producttype', id_producttype);
		$('.sldi_addtocart .addtocart').attr('data-variant', id_variant);
		*/

        $('#btn-add-to-cart').attr('data-id_product', id_product);
        $('#btn-add-to-cart').attr('data-id_producttype', id_producttype);
        $('#btn-add-to-cart').attr('data-variant', id_variant);

		$('.breadcrumb .active').html(name);
		$('.prod_title').html(brand+' '+name);
		$('.pp_currencysymbol').html(currency_symbol);
		if(region=='jpn'){
			$('.pp_currencyiso').html(currency_iso + ' + Tax');
		}else{
			$('.pp_currencyiso').html(currency_iso);
		}

		$('.sld_description .sldd_text').html(description);
		$('.sld_description .sldspec_text').html(spec);

        if(description==''){
			$('.sldd_text_wrapper').hide();
		}

        if(spec==''){
			$('.sldspec_text_wrapper').hide();
		}

		$('.sld_paymentandsecurity .sldps_text').html(paymentSecurity);
		$('.sld_shipping .sldshipping_text').html(shippingText);

        for(var key in promo){
			var id = key;
			var text = promo[key];
			if(id!='-1'){
				$('.promo_wrapper').append('<p class="promo_disclaimer" style="background-image: url(images/icon_'+id+'.jpg);">'+text+'</p>');
			} else {
				$('.promo_wrapper').append('<p class="promo_disclaimer" style="background-image: url(images/icon_45667.jpg);">'+text+'</p>');
			}
		}

		setOtherProducts(otherproducts);

		var videoLoopI = 0;

		for(var key in videos) {
			if(videoLoopI==-1){
				break;
			}
			var url = videos[key];
			var videoId;
			var videoSource;
			var videoHtml;
			var videoUrl = url;
			var isYoutube = videoUrl.indexOf('youtu') > -1;

			if(isYoutube){
				videoId = youtube_parser(videoUrl);
				videoSource = 'youtube';
			} else {
				var vimeoId = videoUrl.split('/');
				videoId = vimeoId[vimeoId.length - 1];
				videoSource = 'vimeo';
				videoUrl = 'https://player.vimeo.com/video/'+videoId;
			}

			if(videoSource=='vimeo'){
				videoHtml = '<iframe src="https://player.vimeo.com/video/'+videoId+'" width="90%" height="281" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>';
			} else if(videoSource=='youtube'){
				videoHtml = '<iframe width="90%" height="315" src="https://www.youtube.com/embed/'+videoId+'" frameborder="0" allowfullscreen></iframe>';
			}
			$('.sld_videoviewr').append(videoHtml);

			videoLoopI++;
		}

		variantsData = data[0].variants;

		var variantNames = data[0].variant_names;
		var variantsList = new Array();
		var nrOfVariants;
		var vli = 1;

        // defines the type of variants: size, color..
        for(var key in variantNames){
			var variantName = variantNames[key].name;
			var variantId = variantNames[key].id;
			if(variantName != ''){
				variantsList.push(variantName);
				$('.vc_'+vli).addClass('vc_active');
				$('.vc_'+vli).find('.variant_name').text(variantName);
				switch(variantId) {
				    case '1':
				        $('.vc_'+vli).addClass('variant_colors_wrapper');
				        break;
				    case '2':
				        $('.vc_'+vli).addClass('variant_size_wrapper');
				        break;
				    default:
				   		$('.vc_'+vli).addClass('variant_misc_wrapper');
				}
			}
			vli++;
		}// end for


		nrOfVariants = variantsList.length;


        // what happens here..?
		for(var key in variantsData){
			var variant1 = variantsData[key].variant1;
			var variant1_id_type = variantsData[key].variant1_id_type;
			var variant1_type = variantsData[key].variant1_type;
			var hexcolor = variantsData[key].hexcolor;

			if(variant1_id_type != ''){
				var variantExist = $('.vc_1').find('ul li[data-id="'+variant1+'"]').size();
				if(variantExist == 0){

                    if( variant1_id_type != 2 ) // NOT size - apply background color
					    $('.vc_1').find('ul').append('<li data-id="'+variant1+'"><a href="#" style="background-color:'+hexcolor+';" >'+variant1+'</a></li>');
                    else // size - DON´T apply background..
                        $('.vc_1').find('ul').append('<li data-id="'+variant1+'"><a href="#">'+variant1+'</a></li>');
				}
			}
		}

		for(var key in variantsData){

			var variant2 = variantsData[key].variant2;
			var variant2_id_type = variantsData[key].variant2_id_type;
			var variant2_type = variantsData[key].variant2_type;

			if(variant2_id_type != ''){
				var variantExist = $('.vc_2').find('ul li[data-id="'+variant2+'"]').size();
				if(variantExist == 0){
					$('.vc_2').find('ul').append('<li data-id="'+variant2+'"><a href="#">'+variant2+'</a></li>');
				}
			}
		}

		for(var key in variantsData){
			var variant3 = variantsData[key].variant3;
			var variant3_id_type = variantsData[key].variant3_id_type;
			var variant3_type = variantsData[key].variant3_type;

			if(variant3_id_type != ''){
				var variantExist = $('.vc_3').find('ul li[data-id="'+variant3+'"]').size();
				if(variantExist == 0){
					$('.vc_3').find('ul').append('<li data-id="'+variant3+'"><a href="#">'+variant3+'</a></li>');
				}
			}

		}

		var initV1_value = variantsData[0].variant1;
		var initV2_value = variantsData[0].variant2;
		var initV3_value = variantsData[0].variant3;

		$('.vc_1').find('ul li[data-id="'+initV1_value+'"] a').trigger('click');
		$('.vc_2').find('ul li[data-id="'+initV2_value+'"] a').trigger('click');
		$('.vc_3').find('ul li[data-id="'+initV3_value+'"] a').trigger('click');
		$('.vc_1').find('ul li[data-id="'+initV1_value+'"] a').trigger('click');

		var selectedColor = getQueryString('variantcolor');
		$('.vc_1').find('ul li[data-id="'+selectedColor+'"] a').trigger('click');

	});
}

// --------------------------  PRODUCTS DETAIL -------------------------//

var surfboards_id_on_cart = [];

var cart_info = {};

function service_GetCart(){
	$.ajax({
		url: sUrl+'/api/v1/shop/carts'+Cookies.get('token_'+region),
		method: 'GET',
		xhrFields: {
	        withCredentials: true
	    },
        beforeSend: function(xhr){
            xhr.withCredentials = true;
        },
		crossDomain: true,
		context: document.body
	}).done(function(data) {
        if( Cookies.get('token_'+region) == "" ){
            Cookies.set('token_'+region, '/'+data.token );
            Cookies.set("token", Cookies.get("token_"+region) );
        }

		var currency = data.currency;
		var id_cart = data.id_cart;
		var shipping = data.shipping;
		var shipping_text = data.shipping_text;
		var shipping_alt_text = data.shipping_alt_text;
		var subtotal = data.subtotal;
		var subtotalnodiscount = data.subtotalnodiscount;
		
		var tax = data.tax;
		var total = Number(data.total);
		var items = data.items;
		var nrOfItems = items.length;
		var promoCodes = data.promocodes;
		var totalQty = 0;
		var totalgiftvouchers = data.totalgiftvouchers;


		$('.cos_products').empty();
		$('.cpl_body').empty();
		$('.cci_insertedpromocodes').empty();
		$('.discountcodes_insertedcodes').empty();

		$('.cos_products').attr('id', 'cart_'+id_cart);
		$('.cos_products').attr('data-id_cart', id_cart);
		$('.cos_totalprice .ccirr_currency').html(currency.symbol);
		$('.cos_totalprice .ccirr_totalprice').html(total+currency.iso);
		
		$('.currency-symbol').html(currency.symbol);
		$('.currency-iso').html(currency.iso);


        var checkoutLinkElement = $('.checkout_securechckout a');
		var checkoutLinkElementExist = checkoutLinkElement.length;
		if(checkoutLinkElementExist>0){
			var checkoutLinkUrl = checkoutLinkElement.attr('href').split('?')[0];
			checkoutLinkUrl = checkoutLinkUrl+'?token='+data.token+'&id_cart='+id_cart;
			checkoutLinkElement.attr('href', checkoutLinkUrl);
		}
		

		var creditcardprocessor = $('#creditcardprocessor').val();
		if(creditcardprocessor=='mid'){
			window.payment_gateway = 'mid';
		} else {
			window.payment_gateway = data.payment_gateway;
		}

        cart_info.shipping_country_code = data.shipping_info.ship_country;
        cart_info.id_shipping_method = data.shipping_info.id_shipping_method;
        cart_info.total = data.total;
        cart_info.currency = data.currency.iso;

		if(shipping_alt_text!=''){
			$('.t_shippingtext').html(shipping_alt_text);

			$(".t_shippingtext").closest(".ccirr_right").find(".currency-symbol").hide();
			$(".t_shippingtext").closest(".ccirr_right").find(".currency-iso").hide();
		} else {
			if(shipping>0){
				$('.t_shippingtext').html(shipping);

				$(".t_shippingtext").closest(".ccirr_right").find(".currency-symbol").show();
				$(".t_shippingtext").closest(".ccirr_right").find(".currency-iso").show();
			} else {
				$('.t_shippingtext').html(shipping_text);
				
				$(".t_shippingtext").closest(".ccirr_right").find(".currency-symbol").hide();
				$(".t_shippingtext").closest(".ccirr_right").find(".currency-iso").hide();
			}
		}


		totalgiftvouchers = Number(totalgiftvouchers);
		if(totalgiftvouchers=='0'){
			$('.totalgiftvouchers').closest('.ccir_row').hide();
		} else {
			$('.totalgiftvouchers').closest('.ccir_row').show();
		}

		
		/* Verificar se este código funciona no checkout.php */
		var totaldiscount= data.discount;
		var promocodes=data.promocodes;
		
		for(var key in promocodes){
			$('.discountcodes_insertedcodes').append('<span >' + promocodes[key].name + ' - '+  promocodes[key].description + '<sup><a href="" class="promocoderemove"   data-id_webcart2discountcode="' +  promocodes[key].id_webcart2discountcode + '" >X</a></sup></span><br>');
		}

		if(Number(totaldiscount)>0){
			$('.t_discount').html(totaldiscount);
			$('#discount_summary .currency-iso').html(currency.iso);
			$('#discount_summary').show();
		}else{
			$('#discount_summary').hide();
		}
		

        var total_global_itens = 0;

        $('.t_nrofitems, .bmc_nrofitems').text(0);
		
		for(var key in items){
			var id_product = items[key].id_product;
			var id_producttype = items[key].id_producttype;
			var id_variant = items[key].id_variant;
			var img = items[key].img;
			var name = items[key].name;
			var qtdreadonly = items[key].qtdreadonly;
			var qty = items[key].qty;
			var sku = items[key].sku;
			var totalprice = items[key].totalprice;
			var totalpricenodiscount = items[key].totalpricenodiscount;
			var type = items[key].type;
			var unitprice = items[key].unitprice;
			var description = items[key].description;
			totalQty = Number(totalQty)+Number(qty);
			total_global_itens += Number( qty );
			
            if(id_producttype == 1){
                surfboards_id_on_cart.push(id_product);
            }

            var id_producttypeName;
			var productUrl;
			if(id_producttype=='1'){
				id_producttypeName = 'surfboard';
				productUrl = '/shop/surfboards/detail.php?id='+id_product;
			} else if(id_producttype=='2'){
				id_producttypeName = 'accessories';
				productUrl = '/shop/accessories/detail.php?id='+id_product+'&shop=accessories';
			} else if(id_producttype=='3'){
				id_producttypeName = 'apparel';
				productUrl = '/shop/accessories/detail.php?id='+id_product+'&shop=apparel';
			} else if(id_producttype=='4'){
                id_producttypeName = 'custom surfboard';
                productUrl = '#';
            }

			var descriptionString = '';
			for(var key in description){
				var nameDesc = description[key].name;
				var value = description[key].value;
				var id = description[key].id;
				descriptionString += '<span class="'+id_product+'_'+key+'_'+id+'" data-id="'+id+'"><strong>'+nameDesc+':</strong> '+value+'</span>';
			}
			descriptionString += '<span><strong>Qty:</strong> '+qty+'</span>';

            $('.t_nrofitems, .bmc_nrofitems').html( total_global_itens );
            $('.t_subtotal').html(subtotalnodiscount);
            
            
            $('.t_tax').html(tax);
			

            shaperbuddy.shop.amount_total = total.toFixed(2);

            $('.t_total').html(currency.symbol+''+total.toFixed(2)+' '+currency.iso);
            $('.totalgiftvouchers').html(totalgiftvouchers);

			var default_image = '';

            default_image = "'/custom-order/assets/img/sprays/white-board.svg'";

			$('.cos_products').append('																\
            	<div class="cos_item cartproduct product_'+id_product+'" id="'+id_product+'" data-id_product="'+id_product+'" data-id_producttype="'+id_producttype+'" data-qty="'+qty+'" data-id_variant="'+id_variant+'">	\
					<div class="col-xs-3 cart-product-img-col">															\
						<div class="cosi_img">														\
							<a href="'+productUrl+'">												\
								<img src="'+img+'" onerror="this.src='+default_image+'" class="img-responsive">							\
							</a>																	\
						</div>																		\
					</div>																			\
					<div class="col-xs-6">															\
						<div class="cpl_productdesc">												\
							<p class="cplpd_ref">'+sku+'</p>										\
							<p class="cplpd_name">'+name+'</p>										\
							<p class="cplpd_aditionalinfo">'+descriptionString+'</p>				\
						</div>																		\
					</div>																			\
					<div class="col-xs-3">															\
						<div class="cpl_deleteproduct_wrapper">													\
							<a href="#"><i class="glyphicon glyphicon-remove"></i></a>							\
						</div>																					\
						<div class="cosi_subtotal">																\
							<span class="subtotal_label">Sub-Total</span>										\
							<br>																				\
							<span class="subtotal_value">'+currency.symbol+' '+totalprice+' '+currency.iso+'</span>		\
							<div class="totalpricenodiscount"></div>                                            \
						</div>																					\
					</div>																						\
					<div class="clear_both">&nbsp;</div>														\
				</div>																							\
			');

			
			if(totalprice!=totalpricenodiscount){
				$('.product_'+id_product+' .subtotal_value').html(totalprice+' '+currency.iso);
				$('.product_'+id_product+' .totalpricenodiscount').html(totalpricenodiscount+' '+currency.iso);
			} else {
				$('.product_'+id_product+' .totalpricenodiscount').html('');
			}


			var cplItem = $('.cplitem_dummiecontainer .cpl_item').clone();
			cplItem.attr('data-id_product', id_product);
			cplItem.attr('data-id_producttype', id_producttype);
			cplItem.attr('data-qty', qty);
			cplItem.attr('data-id_variant', id_variant);

			cplItem.find('.cpl_img img').attr('src', img);
			cplItem.find('.cpl_img a').attr('href', productUrl);
			cplItem.find('.cplpd_ref').html(sku);
			cplItem.find('.cplpd_name').html(name);
			cplItem.find('.cplpd_aditionalinfo').html(descriptionString);
			cplItem.find('.cpl_pricecurrency').html(currency.symbol);
			cplItem.find('.cpl_pricevalue').html(unitprice);
			cplItem.find('.cplqs_value input').val(qty);
			cplItem.find('.cplh_totalcurrency').html(currency.symbol);
			cplItem.find('.cplh_totalprice').html(totalprice+currency.iso);

            if(qtdreadonly=='true'){
				cplItem.find('.cpl_quantityselect').attr('qtdreadonly', true).addClass('qtdreadonly_true');
			}

			$('.cpl_body').append(cplItem);
			$('.bmc_nrofitems').html(totalQty);
		}

		checkGoToCheckoutButton();

        $(document).trigger('cart-loaded');

        if( Cookies.get('token_'+region) == "" ){
            Cookies.set('token_'+region, '/'+data.token );
            Cookies.set("token", Cookies.get("token_"+region) );
        }
		
        if( window.location.pathname == '/checkout_final.php' && data.shipping_info.id_shipping_method ){        
			$('#delivery-option-home').trigger('click');


        }else if( window.location.pathname == '/checkout_final.php' && data.shipping_info.id_shipping_method == "" ){
			$(document).on('change', 'form.checkout_final:not(#id_shipping_method)', function(e){
				var isShippingFormOpen = $('#delivery-option-home').prop('checked') || $('#delivery-option-pick-up').prop('checked');
				if(isShippingFormOpen) {
					service_GetCheckoutInfo(e);
				}
			});
        }
	}).fail( function(xhr, textStatus, errorThrown){
        $(document).trigger('cart-loaded');
    });
}













function service_AddToCart(id_product, id_producttype, id_variant, qty, elementTrigger, appointment_date, appointment_time){
	var json = [
		{
			id_product: ''+id_product+'',
			id_producttype: ''+id_producttype+'',
			id_variant: ''+id_variant+'',
			qty: ''+qty+'',
			type: 'product',
			token: Cookies.get('token_'+region).replace('/',''),
			appointment_date: appointment_date,
			appointment_time: appointment_time
		}
	];

	$.ajax({
		url: sUrl+'/api/v1/shop/carts'+Cookies.get('token_'+region),
		method: 'POST',
		data: JSON.stringify(json),
		contentType: 'application/json',
		dataType: 'json',
		xhrFields: {
	        withCredentials: true
	    },
		crossDomain: true,
		context: document.body
	}).done(function(data) {
		// this is needed, also on other sites
		if( Cookies.get('token_'+region) == "" ){
			Cookies.set('token_'+region, '/'+data.token );
			Cookies.set("token", Cookies.get("token_"+region) );
		}

		service_GetCart();
		
		if(elementTrigger!=undefined && elementTrigger!=''){
			if(!elementTrigger.hasClass('prevent_showcart')){
				var isCartOpen = $('.mycart_contents').attr('data-open');
				if(isCartOpen == 'false'){
					$('.btn_mycart a').trigger('click');
				}
			}
		} else {
			var isCartOpen = $('.mycart_contents').attr('data-open');
			if(isCartOpen == 'false'){
				$('.btn_mycart a').trigger('click');
			}
		}

		checkGoToCheckoutButton();


		setTimeout(function(){
			$('.mycart_contents').stop().fadeOut(300, function(){
				$('.mycart_contents').attr('data-open', 'false');
			});
		}, 5000);

		$('#btn-add-to-cart').removeClass('addingToCart');
	});
}

function service_DeleteFromCart( id_product, id_producttype, id_variant, qty ){
	var json = [
		{
			id_product: ''+id_product+'',
			id_producttype: ''+id_producttype+'',
			id_variant: ''+id_variant+'',
			qty: ''+qty+'',
			type: 'product',
			token: Cookies.get('token_'+region).replace('/','')
		}
	];

	$.ajax({
		url: sUrl+'/api/v1/shop/carts'+Cookies.get('token_'+region),
		method: 'DELETE',
		data: JSON.stringify(json),
		contentType: 'application/json',
		dataType: 'json',
		xhrFields: {
	        withCredentials: true
	    },
		crossDomain: true,
		context: document.body
	}).done(function(data) {

		service_GetCart();
		
		checkGoToCheckoutButton();

        $( document ).trigger('cart-loaded');

        surfboards_id_on_cart = jQuery.grep( surfboards_id_on_cart, function(value) {
            return value != id_product;
        });

	})
}

function checkGoToCheckoutButton(){
	var nrOfItemsInCart = $('.checkout_productlist .cpl_body .cartproduct').size();
	if(nrOfItemsInCart==0){
		$('.securechckout_big').hide();
	} else {
		$('.securechckout_big').show();
	}
}



$(function(){
	// ----- POST ----- //
	//$(document).on('click', '.addtocart', function(e){
    $(document).on('click', '#btn-add-to-cart', function(e){
		e.preventDefault();
		var t = $(this);

		if(t.hasClass('addingToCart')){
			return;
		}

		var id_product = Number(t.attr('data-id_product'));
		var id_producttype = Number(t.attr('data-id_producttype'));
		var id_variant = t.attr('data-variant');
		var qty = Number(t.closest('.sldi_addtocart').find('.addproduct_qty').val());
		var isSingleQty = t.hasClass('addtocart_singleqty');
		
		if(isSingleQty){
			qty=1;
		}
		

		var appointment_date = '';
		var appointment_time = '';
		var hasAppointment = $('.apointmentdate_wrapper').length == 1 ? true : false;
		if(hasAppointment) {
			appointment_date = $('.apointment_time').attr('data-date');
			appointment_time = $('.apointment_time').val();
		}

		$('#btn-add-to-cart').addClass('addingToCart');

		service_AddToCart(id_product, id_producttype, id_variant, qty, '', appointment_date, appointment_time);
	});

	// ----- DELETE ----- //
	//$(document).on('click', '.cpl_deleteproduct', function(e){
	$(document).on('click', '.cpl_deleteproduct_wrapper .glyphicon-remove, .cpl_deleteproduct', function(e){
		e.preventDefault();
		var t = $(this);
		var item = t.closest('.cartproduct');
		var id_product = item.attr('data-id_product');
		var id_producttype = item.attr('data-id_producttype');
		var id_variant = item.attr('data-id_variant');
		var qty = item.attr('data-qty');

		t.remove();
		item.fadeOut(100);
		service_DeleteFromCart(id_product, id_producttype, id_variant, qty);
	});
});


//when? - checkout_final.php
function service_GetCheckoutInfo(e){
	var formData = $('.checkout_final').serializeArray();
	var formDataArray;
	var formDataString = '{ '
	for(var key in formData){
		var name = formData[key].name;
		var value = formData[key].value;
		formDataString += '"'+name+'": "'+value+'", ';
	}

	//Cookies.get('token')
	formDataString += '"token" : "'+Cookies.get('token_'+region).replace('/','')+'", ';
	formDataString = formDataString.slice(0, -2);
	formDataString += ' }'
	formDataArray = jQuery.parseJSON(formDataString);


	var useShippingAddressForBilling = $('.shipbillingaddresscheck input').prop('checked');

	if(useShippingAddressForBilling){

		formDataArray.bill_address1 = formDataArray.ship_address1;
		formDataArray.bill_address2 = formDataArray.ship_address2;
		formDataArray.bill_city = formDataArray.ship_city;
		formDataArray.bill_company_name = formDataArray.ship_company_name;
		formDataArray.bill_country = formDataArray.ship_country;
		formDataArray.bill_instructions = formDataArray.ship_instructions;
		formDataArray.bill_state = formDataArray.ship_state;
		formDataArray.bill_zipcode = formDataArray.ship_zipcode;

	}

	// remove shipping_method se for escolhido pickup my order
    if( $("input[name=delivery-option]:checked").val() == "pick-up" ){
        formDataArray["id_shipping_method"]="";
        $(".coconfirm_clientdetails_inner .cci_titleleft").text("You’re Picking up your order from:");
    // remove id_pickuplocation se nao for escolhido pickup my order
    }else{
        formDataArray["id_pickuplocation"]="";
        $(".coconfirm_clientdetails_inner .cci_titleleft").text("We're going to send your order to:");
    }

	// if not body..? why and when?
	//if(e.delegateTarget.activeElement.tagName!='BODY' || e.delegateTarget.activeElement.tagName!='body'){
	if( 1 == 1 ){
		$.ajax({
			url: sUrl+'/api/v1/shop/carts/checkout'+Cookies.get('token_'+region),
			method: 'POST',
			data: JSON.stringify(formDataArray),
			contentType: 'application/json',
			dataType: 'json',
			xhrFields: {
		        withCredentials: true
		    },
			crossDomain: true,
			context: document.body
		}).done(function(data) {
			var currency = data.currency;
			var id_cart = data.id_cart;
			var shipping = data.shipping;
			var shipping_text = data.shipping_text;
			var shipping_alt_text = data.shipping_alt_text;
			var subtotal = data.subtotal;
			var subtotalnodiscount = data.subtotalnodiscount;
			var tax = data.tax;
			var total = Number(data.total);
			var items = data.items;
			var nrOfItems = items.length;
			var promoCodes = data.promocodes;
			var giftvouchers = data.giftvouchers;
			var totalgiftvouchers = data.totalgiftvouchers;		

			if(shipping_alt_text!=''){
				$('.t_shippingtext').html(shipping_alt_text);
	
				$(".t_shippingtext").closest(".ccirr_right").find(".currency-symbol").hide();
				$(".t_shippingtext").closest(".ccirr_right").find(".currency-iso").hide();
			} else {
				if(shipping>0){
					$('.t_shippingtext').html(shipping);
	
					$(".t_shippingtext").closest(".ccirr_right").find(".currency-symbol").show();
					$(".t_shippingtext").closest(".ccirr_right").find(".currency-iso").show();
				} else {
					$('.t_shippingtext').html(shipping_text);
					
					$(".t_shippingtext").closest(".ccirr_right").find(".currency-symbol").hide();
					$(".t_shippingtext").closest(".ccirr_right").find(".currency-iso").hide();
				}
			}

			totalgiftvouchers = Number(totalgiftvouchers);

			if(totalgiftvouchers=='0'){
				$('.totalgiftvouchers').closest('.ccir_row').hide();
			} else {
				$('.totalgiftvouchers').closest('.ccir_row').show();
			}
			
			
			


			$('.cos_products').attr('id', 'cart_'+id_cart);
			$('.cos_products').attr('data-id_cart', id_cart);
			$('.cos_totalprice .ccirr_currency').html(currency.symbol);
			$('.cos_totalprice .ccirr_totalprice').html(total.toFixed(2));

			
			$('.t_subtotal').html(subtotalnodiscount + currency.iso);
			
			$('.t_tax').html(tax);
			$('.t_shippingtext_currency').html(currency.symbol);
			$('.t_shippingtext_currency_iso').html(currency.iso);
			
			
			$('.totalgiftvouchers').html(totalgiftvouchers);
			$('.t_total_currency').html(currency.symbol);
			$('.t_total').html(total.toFixed(2));
			// ------------------------ //


			if($(e.target).hasClass('shippingmethodtrigger')){
				service_GetShippingMethod();
			}

			var selectedShipingMethod = data.shipping_info.id_shipping_method;
			$('.shipping_method').val(selectedShipingMethod);




			$('.giftvoucher_insertedcodes').empty();
			for(var key in giftvouchers){
				var code = giftvouchers[key].code;
				var value = giftvouchers[key].value;
				$('.giftvoucher_insertedcodes').append('<span>'+code+'</span> - $<span>'+value+'</span><br>');
			}


			var shipping_info = data.shipping_info;
			var ship_address1 = shipping_info.ship_address1;
			var ship_city = shipping_info.ship_city;
			var ship_zipcode = shipping_info.ship_zipcode;
			var ship_state_name = shipping_info.ship_state_name;
			var ship_country_name = shipping_info.ship_country_name.ship_country_name;

			$('.finalcheckout_address').html('		\
				<p>'+ship_address1+'</p>			\
				<p>'+ship_zipcode+'</p>				\
				<p>'+ship_city+'</p>				\
				<p>'+ship_state_name+'</p>			\
				<p>'+ship_country_name+'</p>		\
			');
			
		});
	}else{
		$.ajax({
			url: sUrl+'/api/v1/shop/carts'+Cookies.get('token_'+region),
			method: 'GET',
			xhrFields: {
		        withCredentials: true
		    },
			crossDomain: true,
			context: document.body
		}).done(function(data) {
			var currency = data.currency;
			$('.cos_totalprice .ccirr_currency').html(currency.symbol);
			$('.t_shippingtext_currency').html(currency.symbol);
	        	$('.t_shippingtext_currency_iso').html(currency.iso);
			$('.t_total_currency').html(currency.symbol);
			$('.t_total_currency_iso').html(currency.iso);
		});	
	}
}





function service_GetShippingMethod(){

    //$('.shipping_method').empty();

    // added and empty option to not add price of shipping
    //$('.shipping_method').append('<option value="">please select</option>');

	var t = $(this);
	//var wrapper = t.closest('.calculateshipping_wrapper');
	var wrapper = t.closest('.shipping_address');
	
	/*
	var ship_country = wrapper.find('.country_wrapper select').val();
	var ship_state =  wrapper.find('.state_wraper select').val();
	var ship_zipcode = wrapper.find('.zipcode_wraper input').val();
	*/
	
	var ship_country =  $('#ship_country option:selected').val();

	var ship_state =  $('#ship_state option:selected').val();
	var ship_zipcode = wrapper.find('.zipcode_wraper input').val();
	
	return $.when(

		$.ajax({
			//url: sUrl+'/api/v1/shop/carts/shipping_methods?ship_country='+ship_country+'&ship_state='+ship_state+'&ship_zipcode='+ship_zipcode,
			url: sUrl+'/api/v1/shop/carts/shipping_methods'+Cookies.get('token_'+region)+'?ship_country='+ship_country+'&ship_state='+ship_state+'&ship_zipcode='+ship_zipcode,
			method: 'GET',
			xhrFields: {
	                withCredentials: true
	            },
	                crossDomain: true,
	  		context: document.body
		}).done(function(data) {		
			$('.shipping_method').empty();
			$('.shipping_method').append('<option value=""></option>');
			for(var key in data){
				var id_shipping_method = data[key].id_shipping_method;
				var name = data[key].name;
				var price = data[key].price;
				$('.shipping_method').append('<option value="'+id_shipping_method+'">'+name+'</option>');
			}
			/*
			if(cart_info.id_shipping_method && data.length > 1)
				$('.shipping_method').val( cart_info.id_shipping_method ).change();			
			else				
				$('.shipping_method').val( $(".shipping_method option:first" ).val() ).change();
			*/
		})
	)
}



function getCountrys(){
	return $.when(
		$.ajax({
			url: sUrl+'/api/v1/countries?lang=en',
			method: 'GET',
			context: document.body
		}).done(function(data) {
			$('.country_wrapper select').empty();
			var data = data.countries;
			for(var key in data){
				var iso = data[key].iso;
				var name = data[key].name;
				var selected = data[key].selected;
				if(selected){
					selected = 'selected'
				} else {
					selected = '';
				}
				$('.country_wrapper select').append('<option value="'+iso+'" '+selected+'>'+name+'</option>');
			}
			$('.country_wrapper select').trigger('change');
			$( document ).ready( function(){
				$( document ).trigger('countries-loaded')
			})
		})
	)
}

function getStates(iso, target){
	return $.when(
		$.ajax({
			url: sUrl+'/api/v1/countries/'+iso+'/states?lang=en',
			method: 'GET',
			//context: document.body
		}).done(function(data) {

			if(target==undefined){
				$('.state_wraper select').empty();
				$('.state_wraper select').append('<option></option>');
		        //$('#ship_state').change();
			} else {
				$('.'+target).empty();
				$('.'+target).append('<option></option>');
			}			

	        var data = data.states;

			for(var key in data){
				var iso = data[key].iso;
				var name = data[key].name;
				if(target==undefined){
					$('.state_wraper select').append('<option value="'+iso+'">'+name+'</option>');
				} else {
					$('.'+target).append('<option value="'+iso+'">'+name+'</option>');
				}
			}// end for

	        //if( data.length > 0 )
	            $('#ship_state').change();

	           if( data.length == 0){
	           	$("#"+target).closest(".state_wraper").fadeOut("slow");
	           }else{
	           	$("#"+target).closest(".state_wraper").fadeIn("slow");	
	           }

	           $( document ).trigger('states-loaded');

		})

	)	

}


function get_PaymentMethods(){
	$.ajax({
		url: sUrl+'/api/v1/shop/carts/payment_methods',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var data = data.payment_methods;
		for(var key in data){
			var name = data[key].name;
			var available = data[key].available;
			if(available){
				$('.pm_'+name).show();
			}
		}
	});
}





function service_SubmitOrder(){
	var cardholderName = document.getElementById('cardholder-name');
	$.ajax({
		url: sUrl +'/api/v1/shop/paymentgateway/stripe'+Cookies.get('token'),
		context: document.body
	}).done(function(data){
		var clientSecret = data.client_secret;
		
		stripe.handleCardPayment(
			clientSecret, cardElement, {
				payment_method_data: {
					billing_details: {name: cardholderName.value}
				}
			}
		).then(function(result) {
			if (result.error) {
				var message = result.error.message;
				$('.submitwindow_error').fadeIn();
				$('.swe_errormessage').html(message);
			} else {
				var order_no = result.paymentIntent.description;
				$('.sw_ordercode').html(order_no);
				$('.submitwindow_success').fadeIn();
				Cookies.remove("token");
			}
		});
	}).error(function(data){
		var response = data.responseJSON;
		var message = response.errors;
		var outputMessage = '';
		
		for (var key in message) {
			outputMessage = outputMessage+'; '+message[key];
		}
		outputMessage=outputMessage.substring(2);
		
		$('.submitwindow_error').fadeIn();
		$('.swe_errormessage').html(outputMessage);
	});
}

/*
$(function(){
    $(document).on('click', '.checkout_submitorder', function(e){
		e.preventDefault();

		
        service_SubmitOrder();

        $('.submitwindow').fadeIn();
		$('#checkoutfinal_modal .close').trigger('click');
	});
});
*/




/*try to replace this by PHP & CURL*/
function service_Contacts(){
	$.ajax({
		url: sUrl+'/api/v1/contacts',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var target = $('.contacts_factory');
		var labelAddress = data.labels.txt_address;
		var labelPhone = data.labels.txt_sales_phone;
		var labelEmail = data.labels.txt_email_sales;
		var labelOpeningHours = data.labels.txt_workinghours;
		var country = data.country;
		var address = data.address;
		var phone = data.phone_sales;
		var email = data.email_sales;
		var openingHours = data.business_hours;

		var lat = data.gps_lat;
		var lng = data.gps_long;
		var coordinates = new google.maps.LatLng(lat,lng);

		target.find('.ci_address strong').html(labelAddress);
		target.find('.ci_contacts .cic_phone strong').html(labelAddress);
		target.find('.ci_contacts .cic_email strong').html(labelEmail);
		target.find('.ci_hours strong').html(labelOpeningHours);
		target.find('.contacts_title span').html(country);
		target.find('.ci_address div').html(address).append('<br>'+country);
		target.find('.ci_contacts .cic_phone div').html(phone);
		target.find('.ci_contacts .cic_email div').html(email);
		target.find('.ci_hours div').html(openingHours);

		setTimeout(function(){
			initCFactoryMap(coordinates);
		}, 1000);
	});


	$.ajax({
		url: sUrl+'/api/v1/contacts',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var target = $('.contacts_shop');
		var labelAddress = data.labels.txt_address;
		var labelPhone = data.labels.txt_sales_phone;
		var labelEmail = data.labels.txt_email_sales;
		var labelOpeningHours = data.labels.txt_workinghours;
		var country = data.country;
		var address = data.address;
		var phone = data.phone_sales;
		var email = data.email_sales;
		var openingHours = data.business_hours;

		var lat = data.gps_lat;
		var lng = data.gps_long;
		var coordinates = new google.maps.LatLng(lat,lng);

		target.find('.ci_address strong').html(labelAddress);
		target.find('.ci_contacts .cic_phone strong').html(labelAddress);
		target.find('.ci_contacts .cic_email strong').html(labelEmail);
		target.find('.ci_hours strong').html(labelOpeningHours);
		target.find('.contacts_title span').html(country);
		target.find('.ci_address div').html(address).append('<br>'+country);
		target.find('.ci_contacts .cic_phone div').html(phone);
		target.find('.ci_contacts .cic_email div').html(email);
		target.find('.ci_hours div').html(openingHours);


		setTimeout(function(){
			initCShopMap(coordinates);
		}, 1000);
	});
}

//surfboard details
function service_SurfboardModelDetail(){

	//alert();

	// Isto deixa USa buscar em USA e EUR/AUS buscar em AUS
	var endpoint = sUrlWebsite;
	if( region=="usa" || region=="eur"  || region=="bali"   || region=="bra" ){
		endpoint = sUrl;
	}

	
	var surfboardmodelId = getQueryString('id');
	$.ajax({
		url: endpoint+'/api/v1/surfboardmodels/'+surfboardmodelId +'?lang=en',
		method: 'GET',
		context: document.body
	}).done(function(data) {

        	if( data.length>0 ){

			var id_surfboardmodel = data[0].id_surfboardmodel;
			var surfboardmodel = data[0].surfboardmodel;
			var brand = data[0].brand;
			var images = data[0].img;
			var wavesize_min = data[0].wavesize.min;
			var wavesize_max = data[0].wavesize.max;
			var skilllevel = data[0].skilllevel;
			var skillString = '';
			var surfboardmodeltype = data[0].surfboardmodeltype;
			var description = data[0].description;
			var img_logo = data[0].img_logo;
			var technology = data[0].technology;
			var price = data[0].min_price;
			var currencySymbol = data[0].currency.symbol;
			var currencyIso = data[0].currency.iso;
			var shopavailable = data[0].shopavailable;
			var features = data[0].features;
			//if( data[0].bottom.length == 0 ){
	        if( data[0].bottom.img == '' ){
	            $('.boardbottomfeatures').remove();
			} else {
				var bottomImg = data[0].bottom.img;
				var bottomText = data[0].bottom.text;
			}
			if(data[0].videos.length==0){
				var videoUrl = '';
			} else {
				var videoUrl = data[0].videos[0].url;
				//assign url to social share
				$('.social-share-video-link').each(function(){
					initial_href = this.href;
					final_href = initial_href += videoUrl;
					this.href = final_href;
				});

			}
			var standard_dimensions = data[0].standard_dimensions;
			var other_models = data[0].other_models;




			if(price==''){
				$('.bdp_price').remove();
			}
			// --- BOARD IMAGE SLIDER
			$('.surfboarddetail_carousel .carousel-indicators').empty();
			var crslIndex = 0;
			for(var key in images){
				var imgUrl = images[key].img1;
				var cover = images[key].cover;
				if(cover==1){
					$('.surfboarddetail_carousel .carousel-indicators').prepend('						\
						<li data-target="#surfboarddetail_slider" data-slide-to="'+crslIndex+'">		\
					    	<div class="carouselindicator_inner">										\
						    	<img src="'+imgUrl+'" class="img-responsive">							\
						    	<div class="board_shadow">												\
									<img src="/images/boardswidget_shadow.png">							\
								</div>																	\
							</div>																		\
					    </li>																			\
					');
					$('.surfboarddetail_carousel .carousel-inner').prepend('	\
					<div class="item">											\
				      <img src="'+imgUrl+'" alt="">								\
				    </div>														\
				');
				} else{
					$('.surfboarddetail_carousel .carousel-indicators').append('						\
						<li data-target="#surfboarddetail_slider" data-slide-to="'+crslIndex+'">		\
					    	<div class="carouselindicator_inner">										\
						    	<img src="'+imgUrl+'" class="img-responsive">							\
						    	<div class="board_shadow">												\
									<img src="/images/boardswidget_shadow.png">							\
								</div>																	\
							</div>																		\
					    </li>																			\
					');
					$('.surfboarddetail_carousel .carousel-inner').append('		\
					<div class="item">											\
				      <img src="'+imgUrl+'" alt="">								\
				    </div>														\
				');
				}

				crslIndex++;
			}
			var setImgNrI = 0;
			$('.surfboarddetail_carousel .carousel-indicators > li').each(function(){
				var t = $(this);
				t.attr('data-slide-to', setImgNrI);
				setImgNrI++;
			});
			$('.surfboarddetail_carousel .carousel-indicators li:first').addClass('active');
			$('.surfboarddetail_carousel .carousel-inner .item:first').addClass('active');


			// --- MISC
			$('.breadcrumb .active').html(surfboardmodel);
			$('.bdpts_brand').html(brand);
			$('.bdpts_surfboardmodel').html(surfboardmodel);

			/*
			$('.bdpts_ws_min').html(wavesize_min);
			$('.bdpts_ws_max').html(wavesize_max);
			*/

			/*
			for(var key in skilllevel){
				var skill = skilllevel[key].name;
				skillString += skill+', ';
			}
			*/

			skillString = skillString.slice(0, -2)
			$('.bdpts_skilllevel').html(skillString);
			$('.bdpts_surfboardmodeltype').html(surfboardmodeltype);
			$('.bdp_textdesc_text').html(description);
			if(technology.length==0){
				$('.bdp_textdesc_technology').remove();
			} else {
				for(var key in technology){
					var imgUrl = technology[key].img;
					$('.bdp_textdesc_technology .bdp_textdesc_technology_imgs').append('<img src="'+imgUrl+'">');
				}
			}
			$('.bdp_logo').empty();
			//$('.bdp_logo').append('<img src="'+img_logo+'"></img>');
	        $('#model-logo').append('<img src="'+img_logo+'" class="img-responsive">');
			$('.sd_boardname').text(surfboardmodel);
			$('.vhbd_boardname').text(surfboardmodel);



			//if( region=="aus" ){
				// Preço
				$('.bdp_pv_price').html(price);
				$('.bdp_pv_currencysymbol').html(currencySymbol);
				$('.bdp_pv_currencyiso').html(currencyIso);
			//}
			
			
			if( shopavailable > 0 ){
				//$('.bdppl_shop').show().attr('href', '/shop/surfboards/?model='+id_surfboardmodel);
	            //$('#surfboard-buy-stock-btn').fadeIn().attr('href', '/shop/surfboards/?model='+id_surfboardmodel);
	            $('#surfboard-buy-stock-btn').css('display','block').attr('href', '/shop/surfboards/?model='+id_surfboardmodel);
			}
			for(var key in features){
				var imgUrl = features[key].img;
				var name = features[key].name;
				var value = features[key].value;
				$('.bf_list').append('									\
					<div class="col-sm-4 col-xs-12">					\
						<img src="'+imgUrl+'" class="img-responsive">	\
						<p class="bf_featuretitle">'+name+':</p>		\
						<p class="bf_feature">'+value+'</p>				\
					</div>												\
				');
			}

			$('.boardbottomfeatures_imgwrapper img').attr('src', bottomImg);
			$('.bbf_disclaimer').html(bottomText);



			// --- VIDEO
			if(videoUrl==''){
				$('.video_home').remove();
			} else {
				var isYoutube = videoUrl.indexOf('youtu') > -1;
				if(isYoutube){
					var videoId = youtube_parser(videoUrl);
					var videoEmbed = '<iframe src="https://www.youtube.com/embed/'+videoId+'" frameborder="0" allowfullscreen></iframe>';
				} else {
					var vimeoId = videoUrl.split('/');
					vimeoId = vimeoId[vimeoId.length - 1];
					var videoEmbed = '<iframe src="https://player.vimeo.com/video/'+vimeoId+'" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>';
				}
				$('.videoembed_wrapper').html(videoEmbed);
			}

			//simple custom order button
			$('#surfboard-custom-order-btn').attr('href','/custom-order?model='+id_surfboardmodel);

			/*if( region=="aus" ){*/
				// --- STANDARD DIMENSIONS
				for(var key in standard_dimensions){
					var t = standard_dimensions[key];
					var size = t.length_inches;
					var width = t.width_inches;
					var thickness = t.thickness_inches;
					var volume = t.volume;
					var weightRange = t.weight_range;
					var tail = t.tail;
					var finOptions = t.fin_options;
					var length_complete = t.length_complete;
					var currentavailability = t.currentavailability;

					var buyQString = 'model='+id_surfboardmodel+'&length='+t.length+'&width='+t.width+'&thickness='+t.thickness;
					//var buyQString = 'model='+id_surfboardmodel+'&length='+length+'&width='+t.width;
					var buyUrl = '/shop/surfboards/?'+buyQString;

					if(currentavailability=='0'){
						buyNowHtml = '<a class="standard-dimensions-table-btn btn-custom-order" href="/custom-order?'+buyQString+'">Custom Order</div>';
					} else {
						buyNowHtml = '<a class="standard-dimensions-table-btn btn-buy-now" href="'+buyUrl+'">Buy Now</div>';
					}
					//var buyNowHtml = '';
					//buyNowHtml = '<a class="sd_buynow" href="'+buyUrl+'">Buy Now</div>';

					$('.standarddimensions table tbody').append('												\
						<tr>																					\
							<td>'+size+'</td>																	\
							<td>'+width+'</td>																	\
							<td>'+thickness+'</td>																\
							<td>'+volume+'</td>																	\
							<td class="hidden-xs">'+weightRange+'</td>															\
							<td class="hidden-xs">'+tail+'</td>																	\
							<td class="hidden-xs">'+finOptions+'</td>																\
							<td>'+buyNowHtml+'</td>																\
						</tr>																					\
					');
				}
			/*}*/	


			for(var key in other_models){
				var t = other_models[key];
				var id_surfboardmodel = t.id_surfboardmodel;
				var img = t.img;
				var surfboardmodel = t.surfboardmodel;
				var min_price = t.min_price;

				$('#othersurfboards_widget .carousel-inner .item .row').append('								\
					<div class="col-xs-2">																		\
		      			<div class="os_imgwrapper">																\
			      			<a href="/surfboards/detail.php?id='+id_surfboardmodel+'">						\
								<div class="board_img">															\
									<img src="'+img+'" class="img-responsive">									\
								</div>																			\
								<div class="board_shadow">														\
									<img src="/images/boardswidget_shadow.png" class="img-responsive">			\
								</div>																			\
								<div class="board_info">														\
									<span class="board_name">'+surfboardmodel+'</span>							\
									<span class="board_price">'+currencySymbol+''+min_price+' '+currencyIso+'</span>							\
								</div>																			\
							</a>																				\
						</div>																					\
		      		</div>																						\
				');
			}
			var widget = $('.othersurfboards');
			otherBoardsInit(widget);

			// skill level SVG
			// insert SVG and play with it					
			Snap.load("/assets/img/surfboards/skill-level.svg", function (data){
				
				Snap('#skill-level-placeholder').append(data);

				$.each( skilllevel, function(k, v){
					
					$('#skill-level #level-'+k+' path').css({'fill':'#000'})

					if( k == 7068 ){
						$('#skill-level #pointer-beginner').css({'fill':'#000'})
					}

					if( k == 7071 ){
						$('#skill-level #pointer-intermediate').css({'fill':'#000'})
					}

					if( k == 11348 ){
						$('#skill-level #pointer-advanced').css({'fill':'#000'})
					}

				})			

			})

			// wave size SVG					
			Snap.load("/assets/img/surfboards/wave-size.svg", function (data){
				
				Snap('#wave-size-placeholder').append(data);

				for( i = wavesize_min; i <= wavesize_max; i++ ){					
					$('#wave-size #size-'+i).css({'fill':'#000'})
				}

				if( wavesize_min == 0 ){
					$('#wave-size #pointer-start').css({'fill':'#000'})
				}

				//if( wavesize_min <= 5 || wavesize_max > 4 ){
					if( wavesize_min <= 5 && wavesize_max >= 5 ){
					$('#wave-size #pointer-middle').css({'fill':'#000'})
				}				

				if( wavesize_max > 9 ){
					$('#wave-size #pointer-end').css({'fill':'#000'})
				}

			})

			$('.ld_item.ld_1 a').attr('href', '/shop/surfboards/?model='+surfboardmodelId );
			$('.ld_item.ld_2 a').attr('href', '/custom-order/?model='+surfboardmodelId );
		}

	});
}









function service_BlogList(){

	$.ajax({
		url: sUrlWebsite+'/api/v1/cms/zones/45/objects',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data){

			var id_cmsconteudo = data[key].id_cmsconteudo;
			var title = data[key].hptitle;
			var postDate = data[key].dt_publication.en;
			//var postResume = data[key].hpresume.substring(0, 100)+' (...)';
            var postResume = data[key].hpresume;
			var multimedia = data[key].multimedia[0];
			if(multimedia!=undefined){
				var multimediatype = multimedia.multimediatype;
				var multimediaContent = '';
				if(multimediatype=='Image'){
					var img = multimedia.filename;
					multimediaContent = '<img src="'+img+'" class="img-responsive" style="width:100%">';
				} else if(multimediatype=='URL'){
					var videoUrl = multimedia.url;
					var isYoutube = videoUrl.indexOf('youtu') > -1;
					var embed = '';
					if(isYoutube){
						var videoId = youtube_parser(videoUrl);
						var embed = '<iframe src="https://www.youtube.com/embed/'+videoId+'" frameborder="0" allowfullscreen></iframe>';
					} else {
						var vimeoId = videoUrl.split('/');
						vimeoId = vimeoId[vimeoId.length - 1];
						var embed = '<iframe src="https://player.vimeo.com/video/'+vimeoId+'" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>';
					}
					multimediaContent = embed;
				}
			}

			var hostname = window.location.hostname;

			$('.blog_list_itemcontainer').append('\
				<div class="row blogitem"> \
					<div class="col-md-12">\
						<a href="detail.php?id='+id_cmsconteudo+'">\
							<div class="row">\
									<div class="col-md-9 col-sm-12">\
										<p class="bi_title">'+title+'</p>\
										<p class="bi_postdate">posted on '+postDate+'</p>\
										<p class="bi_textresume">'+postResume+'</p>\
									</div>\
									<div class="col-md-3 col-sm-12">\
										<div class="bi_postdate">share</div>\
											<ul class="social-share-list">\
												<li>\
													<a href="https://www.facebook.com/sharer/sharer.php?u=http://'+hostname+'/blog/detail.php?id='+id_cmsconteudo+'" target="_blank">\
														<img src="/images/social_fb.png" alt="facebook">\
													</a>\
											</li>\
											<li>\
												<a href="https://twitter.com/intent/tweet?text='+title+' - Chilli Surfboards Blog http://'+hostname+'/blog/detail.php?id='+id_cmsconteudo+'" target="_blank">\
													<img src="/images/social_twitter.png" alt="twitter">\
												</a>\
											</li>\
											<li>\
												<a href="http://plus.google.com/share?url=http://'+hostname+'/blog/detail.php?id='+id_cmsconteudo+'" target="_blank">\
													<img src="/images/social-google-plus.png" alt="google plus">\
												</a>\
											</li>\
											<li>\
												<a href="http://www.tumblr.com/share/link?url=http://'+hostname+'/blog/detail.php?id='+id_cmsconteudo+'" target="_blank">\
													<img src="/images/social-tumblr.png" alt="google plus">\
												</a>\
											</li>\
										</ul>\
									</div>\
							</div>\
							'+multimediaContent+'\
							</a>\
						</div>\
				<div class="row">\
				</div>\
			');
		}
	});
}

function service_BlogDetail(){

	var id_cmsconteudo = getQueryString('id');

    $.ajax({

        url: sUrlWebsite+'/api/v1/cms/zones/45/objects/'+id_cmsconteudo,
		method: 'GET',
		context: document.body

	}).done(function(data) {

        var id_cmsconteudo = data[0].id_cmsconteudo;
		var title = data[0].hptitle;
		var postDate = data[0].dt_publication.en;
		//var postResume = data[0].hpresume;
        var post = data[0].atext || data[0].hpresume;

		//var multimedia = data[0].multimedia[0];
        var multimedia = data[0].multimedia;

        var carousel = '';

		if( multimedia != undefined ){

            var gallery = [];
            var urls = [];

            $.each( multimedia, function( key, value ){
                if( value.multimediatype == 'Image' )
                    gallery.push( value.filename );

                if( value.multimediatype == 'URL' )
                    urls.push( value.url );
            })


            // if images in gallery
            if( gallery.length > 0 ){
                // build itens and indicators
                var itens = indicators = '';

                $.each( gallery, function( key, value ){
                    if( key == 0 ) active = 'active';
                    else active = '';

                    itens += '<div class="item '+active+'">\
                            <img class="first-slide" src="'+value+'" alt="Chiili surfboards">\
                        </div>';

                    indicators += '<li data-target="#post-carousel" data-slide-to="'+key+'" class="'+active+'"></li>';

                });

                var carousel = '<div id="post-carousel" class="carousel slide" data-ride="carousel" data-interval="3000">\
                    <!-- Indicators -->\
                    <ol class="carousel-indicators">'+indicators+'</ol>\
                    <div class="carousel-inner" role="listbox">'+itens+'</div>\
                    <a class="left carousel-control" href="#post-carousel" role="button" data-slide="prev">\
                        <img src="/assets/img/slider/arrow-slider-previous.png" alt="previous" id="previous">\
                        <span class="sr-only">Previous</span>\
                    </a>\
                    <a class="right carousel-control" href="#post-carousel" role="button" data-slide="next">\
                        <img src="/assets/img/slider/arrow-slider-next.png" alt="next" id="next">\
                        <span class="sr-only">Next</span>\
                    </a>\
                </div><hr>';

            }

            var videos = [];

            // if urls ( video - just one, or can it bem more? )
            if( urls.length > 0 ){

                //var links = '<hr><p><strong>Links</strong></p>';

                $.each( urls, function( key, value ){

                    //links += '<a href="'+value+'" target="_blank">'+value+'</a>';

                    var videoUrl = value;
                    var isYoutube = videoUrl.indexOf('youtu') > -1;
                    var embed = '';

                    if(isYoutube){

                        var videoId = youtube_parser(videoUrl);
                        videos.push( '<iframe src="https://www.youtube.com/embed/'+videoId+'" frameborder="0" allowfullscreen></iframe>' );

                    } else {

                        var vimeoId = videoUrl.split('/');
                        vimeoId = vimeoId[vimeoId.length - 1];
                        videos.push( '<iframe src="https://player.vimeo.com/video/'+vimeoId+'?loop=1" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>' );

                    }

                })

            }

            // PBS 26.10.2016 - now it should display all images on a slider, if more than one image exist
            // also, if other types of media exist, they should also appear

            // the previous code does not loop..
            /*

             var multimediatype = multimedia.multimediatype;
             var multimediaContent = '';

            if(multimediatype=='Image'){

                //var img = multimedia.filename;
				//multimediaContent = '<img src="'+img+'" class="img-responsive">';

			} else if(multimediatype=='URL'){

                var videoUrl = multimedia.url;
				var isYoutube = videoUrl.indexOf('youtu') > -1;
				var embed = '';

                if(isYoutube){

					var videoId = youtube_parser(videoUrl);
					var embed = '<iframe src="https://www.youtube.com/embed/'+videoId+'" frameborder="0" allowfullscreen></iframe>';

				} else {

					var vimeoId = videoUrl.split('/');
					vimeoId = vimeoId[vimeoId.length - 1];
					var embed = '<iframe src="https://player.vimeo.com/video/'+vimeoId+'?loop=1" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>';

				}

				multimediaContent = embed;
			}
			*/

		}// end if multimedia exists

		$('.breadcrumb .active').text(title);

		$('.blog_list_itemcontainer').prepend('\
			<div class="blogitem">\
				<p class="bi_title">'+title+'</p>\
				<p class="bi_postdate">'+postDate+'</p>\
				<p class="bi_textresume">'+post+'</p>\
				<p>'+carousel+'</p>\
				<p>'+videos+'</p>\
			</div>\
		');
	});
}












function submitToNewsletter(mail) {
	var email = '{ "email": "'+mail+'" }';
	$.ajax({
		url: sUrl+'/api/v1/subscribers',
		method: 'POST',
		data: email,
		contentType: 'application/json',
		dataType: 'json',
		xhrFields: {
	        withCredentials: true
	    },
		crossDomain: true,
		context: document.body
	}).done(function(data) {
		if(data.subscribe == 'OK'){
			$('#newsletter-sign-up-heading').text('You will be the first to know!');
		}

	});
}
$(function(){
	$(document).on('click', '.ml_submit', function(){

		//alert('here');

		var email = $('.maillist_input').val();
		var isEmailValid = validateEmail(email);
		if(isEmailValid){
			submitToNewsletter(email);
			$('.submit_mailinglist').fadeOut();
		} else {
			$('.maillist_input').addClass('invalid_field');
			$('.maillist_input').closest('.submit_mailinglist').addClass('invalid_field');
		}
	});
	$(document).on('submit', '.submit_mailinglist', function(e){
		e.preventDefault();
	});
	$(document).on('focusin', '.maillist_input', function(){
		$(this).removeClass('invalid_field');
		$(this).closest('.submit_mailinglist').removeClass('invalid_field');
	});
});




















function home_getProducts(){

	/*
	$.ajax({
		url: sUrl+'/api/v1/shop/products/summary',
		method: 'GET',
		context: document.body
	}).done(function(data) {

		var itemsI = 0;

        var loops = 0;

        // holds the build html
        var html = '';

        // on the second row, cols change place, as according to the design
        var push_img = '';
        var pull_text = '';

		for(var key in data){

            itemsI++;

			var surfboardmodel = data[key].surfboardmodel;
			var img = data[key].img.deck;
			var currency = data[key].currency;
			var price = data[key].price;
			var subtitle = data[key].subtitle;
			var id_surfboard = data[key].id_surfboard;
			var id_producttype = data[key].id_producttype;

			var destination = '';
			//if(id_producttype=='1' && id_producttype=='4'){ PBS says: WTF????
            if( id_producttype == '1'){
				destination = '/shop/surfboards/detail.php?id='+id_surfboard;
			} else {
				destination = '/shop/accessories/detail.php?id='+id_surfboard;
			}

            // PBS: build first row
            if( loops == 0 ){

                html = '<div class="row">';

            }

            html +=
            '<div class="col-sm-6 shop-display-item">\
                <div class="row">\
                    <div class="col-sm-5 '+push_img+' col-xs-6 shponlc_prodpic">\
                        <a href="'+destination+'">\
                            <img src="'+img+'" class="img-responsive">\
                        </a>\
                    </div>\
                    <div class="col-sm-7 '+pull_text+' col-xs-6">\
                        <h1>'+surfboardmodel+'</h1>\
                        <p class="shop-display-details">'+subtitle+'</p>\
                        <p class="shop-display-price">'+currency.symbol+' '+price+' '+currency.iso+'</p>\
                        <a href="'+destination+'" class="btn btn-default btn-130x30">buy now</a>\
                    </div>\
                </div>\
            </div>';

            // close actual row and add new
            if( loops == 1 ){

                html += '</div><div class="row border-top">';

                //push_img = 'col-sm-push-7';
                //pull_text = 'col-sm-pull-5';

            }

            loops++;

		} // end for

        // close open row
        html += '</div>';

        $('#shop-display-placeholder-surfboards').append( html );

	});
	*/

    // use same code for accessories and apparel
    // using data-section on the clicked item

    // cache ajax data
    var stored_data = [];

    $('#tab-accessories, #tab-apparel').on('click', function(e) {
        var section = $(this).data('section');
        var loops = 0;
        // holds the build html
        var html = '';
        // on the second row, cols change place, as according to the design
        var push_img = '';
        var pull_text = '';

        // return cached response or get fresh results
        return stored_data[section] || $.ajax({

            url: sUrl + '/api/v1/shop/'+section+'?top=4',
            method: 'GET',
            context: document.body

        }).done(function (data) {
            stored_data[section] = data;
            var itemsI = 0;
            for (var key in data) {
                var id_product = data[key].id_product;
                var brand = data[key].brand;
                var productName = brand+' '+ data[key].name.replace(brand,'');
                var currency = data[key].currency;
                var minprice = data[key].minprice;
                var colors = data[key].variant_colors;
                var nrOfColors = colors.length;
                var tabContent = '';
                var tabNavContent = '';

                if(nrOfColors == 0) {
                    var name = data[key].name;
                    var minprice = data[key].minprice;
                    var mainimg = data[key].mainimg;

                    tabContent += '<div class="tab-pane fade active in" id="prdvariant_' + key + '_1"><img src="' + mainimg + '" class="img-responsive"></div>';
                    tabNavContent = '';
                } else {
                    for (var key2 in colors) {
                        var hexcolor = colors[key2].hexcolor;
                        var img = colors[key2].img;

                        if (key2 == 0) {

                            var firstActive = 'active in';
                            var firstLinkActive = 'active';

                        } else {

                            var firstActive = '';
                            var firstLinkActive = '';

                        }

                        tabContent += '<div class="tab-pane fade ' + firstActive + '" id="prdvariant_' + key + '_' + key2 + '"><img src="' + img + '" class="img-responsive"></div>';
                        tabNavContent += '<li class="' + firstLinkActive + '"><div class="variant_color" href="#prdvariant_' + key + '_' + key2 + '" data-toggle="tab" style="background-color:' + hexcolor + ';" data-colorname="' + colors[key2].name + '" data-id-product="'+id_product+'">' + key2 + '</div></li>';

                    } // end for key in colors

                } // end else



                // PBS: build first row
                if( loops == 0 ){

                    html = '<div class="row">';

                }

                html +=
                    '<div class="col-sm-6 shop-display-item">\
                        <div class="row">\
                            <div class="col-sm-5 '+push_img+' col-xs-6 shponlc_prodpic">\
                                <a href="/shop/accessories/detail.php?id='+id_product+'&shop='+section+'" data-url="/shop/accessories/detail.php?id='+id_product+'&shop='+section+'">\
                                    <div class="tab-content">'+tabContent+'</div>\
                                </a>\
                                <div class="variants_nav">\
								    <ul>'+tabNavContent+'</ul>\
							    </div>\
                            </div>\
                            <div class="col-sm-7 '+pull_text+' col-xs-6">\
                                <h1>'+productName+'</h1>\
                                <p class="shop-display-price">'+currency.symbol+' '+minprice+' '+currency.iso+'</p>\
                                <a href="/shop/accessories/detail.php?id='+id_product+'&shop='+section+'" class="btn btn-default btn-130x30" id="link-product-'+id_product+'" data-initial-url="/shop/accessories/detail.php?id='+id_product+'&shop='+section+'">buy now</a>\
                            </div>\
                        </div>\
                    </div>';

                // close actual row and add new
                if( loops == 1 ){

                    html += '</div><div class="row border-top">';

                    //push_img = 'col-sm-push-7';
                    //pull_text = 'col-sm-pull-5';

                }

                loops++;

            }// end for key in data

            // close open row
            html += '</div>';

            $('#shop-display-placeholder-'+section).append( html );

        }) // end done

    })


    // PBS - default btn does not have link with variant..
    $(document).on('click', '.variant_color', function(){
        var link = $( '#link-product-' + $( this ).data('id-product') );
        link.prop('href',$(link).data('initial-url')+'&variantcolor='+$(this).data('colorname') );
    })
}


function get_ShopHomeList(){
	$.ajax({
		url: sUrl+'/api/v1/shop/surfboards?top=4',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data){
			var surfboardmodel = data[key].surfboardmodel;
			var img = data[key].img.deck;
			var currency = data[key].currency;
			var price = data[key].price;
			var subtitle = data[key].subtitle;
			var id_surfboard = data[key].id_surfboard;

            // PBS: simplify things!
			$('.shophome_surfboards').prepend('\
				<div class="col-sm-3">\
                    <a href="/shop/surfboards/detail.php?id='+id_surfboard+'">\
                        <img src="'+img+'" class="img-responsive center-block">\
                        <h1>'+surfboardmodel+'</h1>\
                        <p>'+subtitle+'</p>\
                        <p class="price">\
                            '+currency.symbol+''+price+'\
                            <span class="currency">'+currency.iso+'</span>\
                        </p>\
                    </a>\
				</div>\
			');
		}
	});



	$.ajax({
		url: sUrl+'/api/v1/shop/accessories?top=4',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data){
			var id_product = data[key].id_product;
			var id_brand = data[key].id_brand;

			var name = data[key].name;
			var currency = data[key].currency;
			var minprice = data[key].minprice;


			var colors = data[key].variant_colors;
			var nrOfColors = colors.length;
			var tabContent = ''; //service_SurfboardModelDetail();
			var tabNavContent = '';

			if(nrOfColors==0){
				var name = data[key].name;
				var minprice = data[key].minprice;
				var mainimg = data[key].mainimg;
				tabContent += '<div class="tab-pane fade active in" id="prdvariant_'+key+'_1"><img src="'+mainimg+'" class="img-responsive"></div>';
				tabNavContent = '';
			} else {
				for(var key2 in colors){
					var name = colors[key2].name;
					var hexcolor = colors[key2].hexcolor;
					var img = colors[key2].img;


					if(key2==0){
						var firstActive = 'active in';
						var firstLinkActive = 'active';
					} else {
						var firstActive = '';
						var firstLinkActive = '';
					}
					tabContent += '<div class="tab-pane fade '+firstActive+'" id="prdvariant_'+key+'_'+key2+'"><img src="'+img+'" class="img-responsive"></div>';
					tabNavContent += '<li class="'+firstLinkActive+'"><div class="variant_color" href="#prdvariant_'+key+'_'+key2+'" data-toggle="tab" style="background-color:'+hexcolor+';" data-colorname="'+name+'">'+key2+'</div></li>';
				}
			}

			$('.shophome_accessories').prepend('\
				<div class="col-sm-3">\
					<div class="shopitem" data-id_product="'+id_product+'" data-id_brand="'+id_brand+'">\
						<a href="/shop/accessories/detail.php?id='+id_product+'&shop=accessories" data-url="/shop/accessories/detail.php?id='+id_product+'&shop=accessories">\
                            <div class="tab-content">'+tabContent+'</div>\
									<h1>'+name+'</h1>\
									<p class="price">\
                                        <span>'+currency.symbol+'</span>\
                                        '+minprice+'<span class="currency"> '+currency.iso+'</span>\
                                        </p>\
								<div class="variants_nav">\
									<ul>'+tabNavContent+'</ul>\
								</div>\
						</a>\
					</div>\
				</div>\
			');
		}

        /*
		setListItemHeight($('.si_img'));
		setTimeout(function(){
			setListItemHeight($('.si_img'));
		}, 100);
		*/

	});



	$.ajax({
		url: sUrl+'/api/v1/shop/apparel?top=4',
		method: 'GET',
		context: document.body
	}).done(function(data) {
		for(var key in data){
			var id_product = data[key].id_product;
			var id_brand = data[key].id_brand;

			var name = data[key].name;
			var currency = data[key].currency;
			var minprice = data[key].minprice;


			var colors = data[key].variant_colors;
			var nrOfColors = colors.length;
			var tabContent = '';
			var tabNavContent = '';

			if(nrOfColors==0){
				var name = data[key].name;
				var minprice = data[key].minprice;
				var mainimg = data[key].mainimg;
				tabContent += '<div class="tab-pane fade active in" id="prdvariant_'+key+'_1"><img src="'+mainimg+'" class="img-responsive"></div>';
				tabNavContent = '';
			} else {
				for(var key2 in colors){
					var name = colors[key2].name;
					var hexcolor = colors[key2].hexcolor;
					var img = colors[key2].img;


					if(key2==0){
						var firstActive = 'active in';
						var firstLinkActive = 'active';
					} else {
						var firstActive = '';
						var firstLinkActive = '';
					}
					tabContent += '<div class="tab-pane fade '+firstActive+'" id="prdvariant_'+key+'_'+key2+'"><img src="'+img+'" class="img-responsive"></div>';
					tabNavContent += '<li class="'+firstLinkActive+'"><div class="variant_color" href="#prdvariant_'+key+'_'+key2+'" data-toggle="tab" style="background-color:'+hexcolor+';" data-colorname="'+name+'">'+key2+'</div></li>';
				}
			}

			$('.shophome_apparel').prepend('\
				<div class="col-sm-3">\
					<div class="shopitem" data-id_product="'+id_product+'" data-id_brand="'+id_brand+'">\
						<a href="/shop/accessories/detail.php?id='+id_product+'&shop=apparel" data-url="/shop/accessories/detail.php?id='+id_product+'&shop=apparel">\
                            <div class="tab-content">'+tabContent+'</div>\
                            <h1>'+name+'</h1>\
                            <p class="price"><span>'+currency.symbol+'</span>'+minprice+'<span class="currency"> '+currency.iso+'</span></p>\
                            <div class="variants_nav">\
                                <ul>'+tabNavContent+'</ul>\
                            </div>\
						</a>\
					</div>\
				</div>\
			');
		}




        /*
		setListItemHeight($('.si_img'));
		setTimeout(function(){
			setListItemHeight($('.si_img'));
		}, 100);
		*/
	});
}


//gets miscellaneous pages
function service_miscpage(id){
	$.ajax({
		url: sUrlWebsite+'/api/v1/cms/zones/47/objects/'+id,
		method: 'GET',
		context: document.body
	}).done(function(data) {
		var headerImg = data[0].multimedia[0].filename;
		var hptitle = data[0].hptitle;
		var atext = data[0].atext;

		$('#chilli_carousel .item img').attr('src', headerImg);
		$('.breadcrumb .active').text(hptitle);
		$('.carousel-caption p').text(hptitle);
		$('.miscpage_container .miscpage_container_inner').append(atext);
	});
}


//PBS 05.2016: instagram sprays
function instagram_sprays(){

    //alert('olé!');

    $.ajax({
        type: "GET",
        dataType: "jsonp",
        cache: false,
        //url: "https://api.instagram.com/v1/users/2326332367/media/recent/?access_token=43180423.0a91f54.5bc57c4d6f1b42289181b61676747075",
        //@pedrosilvashaperbuddy
        url: "https://api.instagram.com/v1/users/2326332367/media/recent/?access_token=3314912590.dd3641f.b0a044bae2bd4e8688db295404f4d42d",
        success: function(response) {
            //first row
            var instagram_sprays_html = '<div class="row">';

            $.each(response.data, function(){
                instagram_sprays_html +=
                '<div class="col-md-4 col-sm-3 col-xs-6 instagram-sprays-col">\
                    <a href="'+this.link+'" target="_blank">\
                        <div class="instagram-sprays-inner">\
                            <div class="instagram-sprays-overlay">'+this.likes.count+'<i class="glyphicon glyphicon-heart"></i></div>\
                            <img src="'+this.images.standard_resolution.url+'" class="img-responsive" alt="instagram spray">\
                        </div>\
                    </a>\
                </div>';

            })

            //close open row
            instagram_sprays_html += '</div>';

            $('#instagram-sprays-container').append( instagram_sprays_html );

            var loops = 0;

            //some anim..
            $.each( $('.instagram-sprays-col'), function(){
                loops++;
                $(this).delay( loops * 500).fadeIn();
            })

        }
    });

}

/**
 *
 * CHECKOUT - ( PAYMENT OPTIONS | SHIPPING OPTIONS | CuSTOMER SERVICE )
 *
 */

// Carrega as informações no Privacy and Policy
function service_getCheckoutTablesInfo(){

	$.ajax({
		url: sUrl+'/api/v1/shop/texts/checkout?lang=en',
		method: 'GET',
		context: document.body
	}).done(function(data) {

		// 1
		// title
		//$(".checkout_disclaimer .table1_info h3").text();
		// content
		$(".checkout_disclaimer .table1_info .cms-content").html( data[0].texto );
		
		// 2
		// title
		//$(".checkout_disclaimer .table2_info h3").text();
		// content
		$(".checkout_disclaimer .table2_info .cms-content").html( data[1].texto );
		// button
		//$(".checkout_disclaimer .table2_info .cdi_btnwrapper a").attr("src", "/shipping.php");
		//$(".checkout_disclaimer .table2_info .cdi_btnwrapper a").text("Check Shipping Rates");
		
		// 3
		// title
		//$(".checkout_disclaimer .table3_info h3").text();
		// content
		$(".checkout_disclaimer .table3_info .cms-content").html( data[2].texto );
		
	});

}

/**
 *
 * Dynamic pages
 *
 */

// Carrega as informações no website
function service_getDynamicPages(_zones, _article){
 	
 	var lang = "en";
 	if (region=="jpn"){
 		lang="ja";
 	}
 	
 	if (region=="chl"){
 		lang="es";
 	}
	
 	
	
	$.ajax({
		url: sUrl+'/api/v1/cms/zones/'+_zones+'/objects/'+_article+'?lang=' + lang,
		method: 'GET',
		context: document.body
	}).done(function(data) {

		for(var key in data){

			// Aplica o Título principal da pagina
			$('.dynamic_wrapper h1.cross').hide().html( "<span class='s1'><strong>"+data[key].hptitle+"</strong></span>"  ).fadeIn();	
			// Aplica o conteudo do texto
			$('.dynamic_wrapper .d_atext').hide().html( data[key].atext ).fadeIn();
			
			
			var headerImg = data[0].multimedia[0].filename;
			var hptitle = data[0].hptitle;
			var atext = data[0].atext;

			$('#chilli_carousel .item img').attr('src', headerImg);
			$('.breadcrumb .active').text(hptitle);
			$('.carousel-caption p').text(hptitle);
			$('.miscpage_container .miscpage_container_inner').append(atext);
			
		}
	});

}