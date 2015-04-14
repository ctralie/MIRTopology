function [ DEMD, DL2, Norms ] = getBeatSyncEMDWavelets( sprefix, dim, BeatsPerWin, beatDownsample )
    addpath('ApproximateWaveletEMD_release');
    addpath('../ImageWarp');
    if nargin < 4
        beatDownsample = 1;
    end
    DL2 = getBeatSyncDistanceMatricesSlow(sprefix, dim, BeatsPerWin, beatDownsample);
    DEMD = cell(size(DL2, 1), 1);
    Norms = zeros(size(DL2, 1), 1);
    parfor ii = 1:size(DL2, 1)
        thisD = reshape(DL2(ii, :), [dim dim]);
        %Normalize mass for EMD
        Norm = sum(thisD(:));
        %Handle the case where there's silence
        if Norm == 0
            Norm = 1;
            thisD = ones(size(thisD))/prod(size(thisD));
        end
        s = wemdn(thisD/Norm, 0);
        Norms(ii) = Norm;
        DEMD{ii} = s';
    end
    DEMD = cell2mat(DEMD);
end

