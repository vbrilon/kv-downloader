
        function activeDownloadBtn() {
            document.querySelector('#mixprod_loader').style.display = "none";
            document.querySelector('#link_addcart_40852').removeAttribute('style');
            document.querySelector('#link_addcart_40852').classList.remove('pointer-events-none');
        }

        var mixer;
        $(document).ready(function () {
            mixer = new Mixer(document.querySelector('.mixer'));
            mixer.setTracksDescription(["<div class='custom__mixer-track-caption-input'><input type='checkbox' id='precount' checked=checked onclick='mixer.setPrecount(this.checked ? 1 : 0);'><a class='tooltip' href='#' onclick='return false;' title=\"This option adds a pre-count click sound before the beginning of the song (useful for instance when the song starts a cappella).\"> Intro count<\/a><\/div><span class='custom__mixer-track-caption-name'>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Click<\/span>","Drum Kit","Bass","Electric Guitar\n(left)","Electric Guitar\n(right)","Electric Guitar\n(crunch 1)","Electric Guitar\n(crunch 2)","Electric Guitar\n(clean)","Distorted Electric Guitar","Lead Electric Guitar\n(left)","Lead Electric Guitar","Backing Vocals","Lead Vocal"]);
            mixer.setPrecount("1");
            mixer.setPitch("0");
            mixer.setLevels("1,0.2,0.3,100.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,0.12,0.13,0");
            mixer.setPannings("1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,0.10,0.11,-100.12,0.13,0");
            mixer.setStrings({
                play: "Play"
                , reset: "Reset"
                , pause: "Pause"
            });
                        mixer.getMixCallback = function () {
                mixer.parameters.bkac = "editf";
                mixer.parameters.s =40852;
                mixer.parameters.prodid =21279320;
                mixer.uri = '/my/begin_download.html?id=21279320&famid=5';
            };
            mixer.editMixCallback = function () {
                document.querySelector('#mixprod_loader').style.display = "block";
                document.querySelector('#link_addcart_40852').classList.add('pointer-events-none');
                document.querySelector('#link_addcart_40852').style.opacity = '0.5';
                var link = document.createElement("a");
                link.setAttribute("href", mixer.uri);
                beginDownload(link);
            };
                                    mixer.init('/i/song/i40852/0/multi.json', 214);

                        pitchMultiKey(40852, 0);
                        document.addEventListener('modalOpen', function () {
                if (newModal.elem.querySelector('.begin-download')) {
                    activeDownloadBtn();
                }
            });
        });
