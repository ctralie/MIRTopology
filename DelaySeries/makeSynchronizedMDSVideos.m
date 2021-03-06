function [] = makeSynchronizedMDSVideos(filename, hopSize, textureWindow, outname, plot3D)
    [DelaySeries, Fs, SampleDelays, FeatureNames] = ...
        getDelaySeriesFeatures(filename, hopSize, 1, textureWindow);
    DelaySeries = DelaySeries(:, [1:9 18:38 47:end]);%Only use MFCC 1-5
    %Put into the range [0, 1]
    minData = min(DelaySeries);
    DelaySeries = bsxfun(@minus, DelaySeries, minData);
    maxData = max(DelaySeries);
    DelaySeries = bsxfun(@times, DelaySeries, 1./(maxData+eps));

    [Y, eigs] = cmdscale(squareform(pdist(DelaySeries)));
    C = colormap;
    N = size(Y, 1);
    Colors = C( ceil( (1:N)*64/N ), :);

    TotalSamples = SampleDelays(end) + hopSize;
    TotalSeconds = TotalSamples/Fs;
    FramesPerSecond = N/TotalSeconds
    
    figure(1);
    for ii = 1:N
        if plot3D == 1
            scatter3(Y(1:ii, 1), Y(1:ii, 2), Y(1:ii, 3), 20, Colors(1:ii, :));
        else
            scatter(Y(1:ii, 1), Y(1:ii, 2), 20, Colors(1:ii, :));
        end
        xlim([min(Y(:, 1)), max(Y(:, 1))]);
        ylim([min(Y(:, 2)), max(Y(:, 2))]);
        if plot3D == 1
            zlim([min(Y(:, 3)), max(Y(:, 3))]);
            view(mod(ii/2, 360), 0);
        end
        print('-dpng', '-r100', sprintf('syncmovie%i.png', ii));
    end
    
    [X, Fs] = audioread(filename);
    
    X = X(1:TotalSamples);
    
    audiowrite('syncmoviesound.wav', X, Fs);
    

    
    system(sprintf('avconv -r %g -i syncmovie%s.png -i syncmoviesound.wav -b 65536k -r 24 %s', FramesPerSecond, '%d', outname));
    system('rm syncmovie*.png');

%     if PLOTEDGES
%         for ii = 1:N-1
%         	plot(Y(ii:ii+1, 1), Y(ii:ii+1, 2), 'Color', Colors(ii, :));
%         end
%     end
end
